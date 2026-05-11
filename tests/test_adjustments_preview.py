import uuid
from io import BytesIO

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageStat

from api.config import settings
from api.routers.adjustments import AdjustmentSource as AdjustmentApiSource
from models.enums import ChromaCleanStrength, ColorGradePreset, CplStrength, DenoiseStrength
from services import (
    adjustments,
    chroma_clean,
    color_grade,
    cpl_look,
    denoise,
    lens_distort,
    photo_processor,
)


def _mean_channel_delta(image: Image.Image, left: int, right: int) -> float:
    mean = ImageStat.Stat(image.convert("RGB")).mean
    return mean[left] - mean[right]


def _difference_sum(left: Image.Image, right: Image.Image) -> float:
    return sum(ImageStat.Stat(ImageChops.difference(left, right)).sum)


def _edge_mean(image: Image.Image) -> float:
    return ImageStat.Stat(image.convert("L").filter(ImageFilter.FIND_EDGES)).mean[0]


def _luma_std(image: Image.Image, box: tuple[int, int, int, int]) -> float:
    return float(np.asarray(image.convert("L").crop(box)).std())


def _luma_mean(image: Image.Image, box: tuple[int, int, int, int]) -> float:
    return float(np.asarray(image.convert("L").crop(box)).mean())


def _mean_chroma_spread(image: Image.Image, box: tuple[int, int, int, int]) -> float:
    arr = np.asarray(image.convert("RGB").crop(box), dtype=np.float32)
    return float((np.abs(arr[:, :, 0] - arr[:, :, 1]) + np.abs(arr[:, :, 2] - arr[:, :, 1])).mean())


def _luma_contrast(
    image: Image.Image,
    dark_box: tuple[int, int, int, int],
    light_box: tuple[int, int, int, int],
) -> float:
    gray = image.convert("L")
    dark = ImageStat.Stat(gray.crop(dark_box)).mean[0]
    light = ImageStat.Stat(gray.crop(light_box)).mean[0]
    return light - dark


class _FakeHttpResponse(BytesIO):
    def __init__(self, body: bytes, content_type: str) -> None:
        super().__init__(body)
        self.headers = {"Content-Type": content_type}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False


class _FakeOpener:
    def __init__(self, responses: list[_FakeHttpResponse]) -> None:
        self.responses = responses
        self.urls: list[str] = []

    def open(self, url: str, timeout: int):
        self.urls.append(url)
        return self.responses.pop(0)


def _mean_squared_error(
    left: Image.Image,
    right: Image.Image,
    box: tuple[int, int, int, int],
) -> float:
    left_arr = np.asarray(left.crop(box), dtype=np.float32)
    right_arr = np.asarray(right.crop(box), dtype=np.float32)
    return float(((left_arr - right_arr) ** 2).mean())


def test_preview_jpeg_downsizes_before_adjustments() -> None:
    image = Image.new("RGB", (2400, 1600), (120, 120, 120))

    payload = adjustments.preview_jpeg(image, {"orientation": 180, "temperature": 100})

    preview = Image.open(BytesIO(payload))
    assert max(preview.size) <= 760


def test_temperature_adjustment_is_visible() -> None:
    image = Image.new("RGB", (32, 32), (128, 128, 128))

    neutral = adjustments.apply_adjustments(image, {})
    warm = adjustments.apply_adjustments(image, {"temperature": 100})

    assert _mean_channel_delta(warm, 0, 2) - _mean_channel_delta(neutral, 0, 2) >= 70


def test_grade_preset_applies_before_manual_adjustments() -> None:
    image = Image.new("RGB", (32, 32), (128, 128, 128))

    graded = adjustments.apply_adjustments(
        image,
        {"grade_preset": "outdoor_warm", "temperature": 0},
    )

    assert _mean_channel_delta(graded, 0, 2) > 20


def test_legacy_distortion_maps_to_horizontal_axis() -> None:
    params = adjustments.normalize_params({"distortion": 42})

    assert params["distortion"] == 42
    assert params["distortion_x"] == 42
    assert params["distortion_y"] == 0


def test_legacy_distortion_matches_x_axis_output() -> None:
    image = Image.new("RGB", (80, 60), (20, 20, 20))
    draw = ImageDraw.Draw(image)
    draw.rectangle((8, 8, 72, 52), outline=(235, 235, 235), width=4)

    legacy = adjustments.apply_adjustments(image, {"distortion": 70})
    x_axis = adjustments.apply_adjustments(image, {"distortion_x": 70})

    assert _difference_sum(legacy, x_axis) == 0


def test_distortion_axis_coefficients_preserve_expected_corner_mapping(monkeypatch) -> None:
    captured: dict[str, list[tuple[float, float]]] = {}

    def capture_coeffs(
        source: list[tuple[float, float]],
        target: list[tuple[float, float]],
    ) -> list[float]:
        captured["source"] = source
        captured["target"] = target
        return [1, 0, 0, 0, 1, 0, 0, 0]

    monkeypatch.setattr(adjustments, "_perspective_coeffs", capture_coeffs)

    adjustments._manual_distortion(Image.new("RGB", (100, 50)), horizontal=50, vertical=-25)

    assert captured["source"] == [(0, 0), (100, 0), (100, 50), (0, 50)]
    assert captured["target"] == [(-4, -1), (104, 1), (96, 49), (4, 51)]


def test_distortion_axes_change_geometry_output() -> None:
    image = Image.new("RGB", (80, 60), (20, 20, 20))
    draw = ImageDraw.Draw(image)
    draw.rectangle((8, 8, 72, 52), outline=(235, 235, 235), width=4)
    draw.line((40, 0, 40, 60), fill=(220, 60, 60), width=3)
    draw.line((0, 30, 80, 30), fill=(60, 120, 220), width=3)

    horizontal = adjustments.apply_adjustments(image, {"distortion_x": 80})
    vertical = adjustments.apply_adjustments(image, {"distortion_y": 80})

    assert _difference_sum(image, horizontal) > 1000
    assert _difference_sum(image, vertical) > 1000
    assert _difference_sum(horizontal, vertical) > 1000


def test_pipeline_night_grade_is_visibly_cooler() -> None:
    image = Image.new("RGB", (32, 32), (128, 128, 128))

    graded = color_grade.apply_grade(image, ColorGradePreset.NIGHT_COLD)

    assert _mean_channel_delta(graded, 2, 0) >= 35


def test_cpl_look_none_preserves_pixels() -> None:
    image = Image.new("RGB", (32, 24), (96, 104, 112))

    result = cpl_look.apply_cpl_look(image, CplStrength.NONE)

    assert _difference_sum(image, result) == 0


def test_cpl_look_reduces_car_interior_glare_without_crushing_dark_trim() -> None:
    image = Image.new("RGB", (120, 80), (28, 30, 32))
    draw = ImageDraw.Draw(image)
    draw.rectangle((8, 12, 112, 68), fill=(34, 36, 38))
    draw.rectangle((18, 20, 102, 34), fill=(18, 20, 22))
    draw.rectangle((42, 42, 78, 58), fill=(16, 90, 170))
    draw.rectangle((82, 42, 108, 58), fill=(224, 220, 208))
    draw.line((20, 27, 100, 27), fill=(238, 238, 232), width=5)
    draw.line((28, 24, 94, 34), fill=(218, 218, 212), width=2)

    result = cpl_look.apply_cpl_look(image, CplStrength.MEDIUM)

    glare_box = (36, 24, 84, 31)
    dark_trim_box = (18, 44, 38, 60)
    screen_box = (46, 44, 74, 56)
    white_leather_box = (86, 45, 104, 55)
    assert _luma_mean(result, glare_box) < _luma_mean(image, glare_box) - 18
    assert _luma_mean(result, dark_trim_box) >= _luma_mean(image, dark_trim_box) - 6
    assert _luma_mean(result, screen_box) >= _luma_mean(image, screen_box) - 8
    assert _luma_mean(result, white_leather_box) >= _luma_mean(image, white_leather_box) - 8


def test_cpl_look_reduces_moderate_dashboard_reflection() -> None:
    image = Image.new("RGB", (120, 72), (26, 27, 29))
    draw = ImageDraw.Draw(image)
    draw.rectangle((12, 14, 108, 58), fill=(24, 25, 27))
    draw.line((20, 35, 100, 35), fill=(190, 190, 184), width=4)

    result = cpl_look.apply_cpl_look(image, CplStrength.MEDIUM)

    glare_box = (32, 33, 88, 38)
    assert _luma_mean(result, glare_box) < _luma_mean(image, glare_box) - 10


def test_chroma_clean_none_preserves_pixels() -> None:
    image = Image.new("RGB", (32, 24), (40, 42, 44))

    result = chroma_clean.apply_chroma_clean(image, ChromaCleanStrength.NONE)

    assert _difference_sum(image, result) == 0


def test_chroma_clean_reduces_dark_false_color_without_washing_yellow() -> None:
    base = Image.new("RGB", (96, 64), (28, 28, 28))
    noisy = np.asarray(base).copy()
    rng = np.random.default_rng(42)
    noise = rng.normal(0, 20, noisy[:, :64, :].shape).astype(np.int16)
    noisy[:, :64, :] = np.clip(noisy[:, :64, :].astype(np.int16) + noise, 0, 255).astype(np.uint8)
    noisy[:, 64:, :] = (216, 155, 28)
    image = Image.fromarray(noisy, mode="RGB")

    result = chroma_clean.apply_chroma_clean(image, ChromaCleanStrength.HIGH)

    dark_box = (0, 0, 64, 64)
    yellow_box = (70, 8, 92, 56)
    assert _mean_chroma_spread(result, dark_box) < _mean_chroma_spread(image, dark_box) * 0.73
    assert _mean_squared_error(result, image, yellow_box) < 8


def test_chroma_clean_preserves_dark_saturated_details() -> None:
    image = Image.new("RGB", (80, 48), (28, 28, 28))
    pixels = np.asarray(image).copy()
    pixels[:, :44] = (30, 32, 34)
    pixels[10:38, 50:72] = (18, 45, 115)
    image = Image.fromarray(pixels, mode="RGB")

    result = chroma_clean.apply_chroma_clean(image, ChromaCleanStrength.HIGH)

    ambient_light_box = (50, 10, 72, 38)
    assert _mean_squared_error(result, image, ambient_light_box) < 3


def test_adjustment_source_accepts_processing_versions() -> None:
    source = AdjustmentApiSource(kind="processing", value=" ai-version-id ")

    assert source.normalized() == {"kind": "processing", "value": "ai-version-id"}


def test_process_photo_writes_immutable_batch_version_path(monkeypatch, tmp_path) -> None:
    project_id = uuid.uuid4()
    photo_id = uuid.uuid4()
    monkeypatch.setattr(settings, "storage_root", tmp_path)
    source = tmp_path / "original.jpg"
    Image.new("RGB", (24, 16), (128, 128, 128)).save(source)

    result = photo_processor.process_photo(
        project_id=project_id,
        photo_id=photo_id,
        source_relative_path="original.jpg",
        preset=ColorGradePreset.SHOWROOM_WHITE,
        denoise_strength=DenoiseStrength.NONE,
        version_number=3,
    )

    assert result.relative_path.endswith(f"{photo_id}.batch-v3.jpg")
    assert (tmp_path / result.relative_path).exists()
    assert not (tmp_path / "projects" / str(project_id) / "processed" / f"{photo_id}.showroom_white.jpg").exists()


def test_opencv_denoise_fallback_reduces_noise(monkeypatch) -> None:
    rng = np.random.default_rng(42)
    noisy = np.clip(128 + rng.normal(0, 28, (64, 64, 3)), 0, 255).astype(np.uint8)
    image = Image.fromarray(noisy, "RGB")

    def fail_nafnet(_rgb: np.ndarray) -> np.ndarray:
        raise denoise.DenoiseError("force fallback")

    monkeypatch.setattr(denoise, "_run_nafnet", fail_nafnet)

    result = denoise.denoise(image, DenoiseStrength.HEAVY)

    before_std = float(np.asarray(image).std())
    after_std = float(np.asarray(result).std())
    assert after_std < before_std * 0.75


def test_heavy_denoise_stays_visible_when_nafnet_is_conservative(monkeypatch) -> None:
    rng = np.random.default_rng(7)
    flat = np.full((96, 96, 3), 48, dtype=np.float32)
    noisy = np.clip(flat + rng.normal(0, 34, flat.shape), 0, 255).astype(np.uint8)
    image = Image.fromarray(noisy, "RGB")

    def conservative_nafnet(rgb: np.ndarray) -> np.ndarray:
        return rgb

    monkeypatch.setattr(denoise, "_run_nafnet", conservative_nafnet)

    result = denoise.denoise(image, DenoiseStrength.HEAVY)

    before_std = float(np.asarray(image).std())
    after_std = float(np.asarray(result).std())
    assert after_std < before_std * 0.75
    assert after_std > before_std * 0.45


def test_medium_denoise_is_visible_when_nafnet_is_conservative(monkeypatch) -> None:
    rng = np.random.default_rng(101)
    clean = Image.new("RGB", (160, 110), (38, 64, 102))
    draw = ImageDraw.Draw(clean)
    draw.rectangle((20, 42, 140, 100), fill=(215, 212, 198))
    for x in range(34, 128, 12):
        draw.line((x, 48, x, 96), fill=(42, 42, 42), width=2)
    noisy = np.clip(
        np.asarray(clean, dtype=np.float32) + rng.normal(0, 24, (110, 160, 3)),
        0,
        255,
    ).astype(np.uint8)
    image = Image.fromarray(noisy, "RGB")

    def conservative_nafnet(rgb: np.ndarray) -> np.ndarray:
        return rgb

    monkeypatch.setattr(denoise, "_run_nafnet", conservative_nafnet)

    result = denoise.denoise(image, DenoiseStrength.MEDIUM)

    sky = (0, 0, 160, 35)
    assert _luma_std(result, sky) < _luma_std(image, sky) * 0.72
    assert _luma_contrast(result, (34, 50, 36, 94), (40, 50, 48, 94)) > 65


def test_medium_denoise_preserves_car_detail_when_stronger(monkeypatch) -> None:
    rng = np.random.default_rng(202)
    clean = Image.new("RGB", (180, 120), (34, 38, 44))
    draw = ImageDraw.Draw(clean)
    draw.rectangle((18, 36, 162, 92), fill=(92, 96, 102))
    draw.rectangle((34, 50, 88, 70), fill=(24, 24, 24))
    for x in range(38, 86, 6):
        draw.line((x, 51, x, 69), fill=(185, 185, 178), width=2)
    draw.rectangle((100, 50, 146, 70), fill=(132, 138, 144))
    for x in range(104, 146, 8):
        draw.line((x, 50, x + 6, 70), fill=(64, 68, 72), width=1)
    draw.ellipse((34, 76, 58, 100), fill=(18, 18, 18), outline=(178, 178, 170), width=2)
    draw.ellipse((122, 76, 146, 100), fill=(18, 18, 18), outline=(178, 178, 170), width=2)
    noisy = np.clip(
        np.asarray(clean, dtype=np.float32)
        + rng.normal(0, 18, (clean.height, clean.width, 1))
        + rng.normal(0, 14, (clean.height, clean.width, 3)),
        0,
        255,
    ).astype(np.uint8)
    image = Image.fromarray(noisy, "RGB")

    def conservative_nafnet(rgb: np.ndarray) -> np.ndarray:
        return rgb

    monkeypatch.setattr(denoise, "_run_nafnet", conservative_nafnet)

    result = denoise.denoise(image, DenoiseStrength.MEDIUM)

    flat_body = (104, 74, 160, 88)
    grille_dark = (40, 54, 43, 68)
    grille_light = (44, 54, 47, 68)
    assert _mean_squared_error(result, clean, flat_body) < _mean_squared_error(image, clean, flat_body) * 0.72
    assert _luma_contrast(result, grille_dark, grille_light) > _luma_contrast(clean, grille_dark, grille_light) * 0.72


def test_medium_and_heavy_denoise_blend_nafnet_with_classical_pass(monkeypatch) -> None:
    image = Image.new("RGB", (16, 16), (128, 128, 128))
    calls: list[DenoiseStrength] = []

    def fake_nafnet(rgb: np.ndarray) -> np.ndarray:
        return np.full_like(rgb, 0.4)

    def fake_opencv(rgb: np.ndarray, strength: DenoiseStrength) -> np.ndarray:
        calls.append(strength)
        assert abs(float(rgb.mean()) - (128 / 255)) < 1e-5
        return np.full_like(rgb, 0.2)

    monkeypatch.setattr(denoise, "_run_nafnet", fake_nafnet)
    monkeypatch.setattr(denoise, "_run_opencv_denoise", fake_opencv)

    medium = np.asarray(denoise.denoise(image, DenoiseStrength.MEDIUM), dtype=np.float32) / 255
    heavy = np.asarray(denoise.denoise(image, DenoiseStrength.HEAVY), dtype=np.float32) / 255

    assert calls == [DenoiseStrength.MEDIUM, DenoiseStrength.HEAVY]
    assert 0.30 < float(medium.mean()) < 0.33
    assert 0.31 < float(heavy.mean()) < 0.33


def test_heavy_denoise_cleans_flat_noise_without_erasing_architecture_lines(monkeypatch) -> None:
    rng = np.random.default_rng(12)
    clean = Image.new("RGB", (160, 110), (38, 64, 102))
    draw = ImageDraw.Draw(clean)
    draw.rectangle((20, 42, 140, 100), fill=(215, 212, 198))
    for x in range(34, 128, 12):
        draw.line((x, 48, x, 96), fill=(42, 42, 42), width=2)
    draw.rectangle((70, 58, 92, 100), outline=(40, 40, 40), width=3)
    noisy = np.clip(
        np.asarray(clean, dtype=np.float32) + rng.normal(0, 24, (110, 160, 3)),
        0,
        255,
    ).astype(np.uint8)
    image = Image.fromarray(noisy, "RGB")

    def conservative_nafnet(rgb: np.ndarray) -> np.ndarray:
        return rgb

    monkeypatch.setattr(denoise, "_run_nafnet", conservative_nafnet)

    result = denoise.denoise(image, DenoiseStrength.HEAVY)

    assert _luma_std(result, (0, 0, 160, 35)) < _luma_std(image, (0, 0, 160, 35)) * 0.75
    assert _luma_contrast(result, (34, 50, 36, 94), (40, 50, 48, 94)) > 65


def test_heavy_denoise_keeps_low_light_portrait_clean_without_oil_painting(monkeypatch) -> None:
    rng = np.random.default_rng(123)
    clean = Image.new("RGB", (220, 220), (16, 22, 35))
    draw = ImageDraw.Draw(clean)
    for y in range(clean.height):
        draw.rectangle((0, y, clean.width, y + 1), fill=(16 + y // 48, 22 + y // 64, 35 + y // 80))
    draw.ellipse((82, 48, 136, 122), fill=(172, 150, 132))
    draw.ellipse((70, 38, 130, 90), fill=(42, 35, 32))
    for i in range(6):
        draw.line((88 + i * 8, 48, 82 + i * 8, 92), fill=(95, 80, 64), width=2)
    draw.polygon([(48, 136), (110, 112), (170, 138), (200, 220), (20, 220)], fill=(78, 107, 122))
    for i in range(5):
        draw.arc((40 + i * 14, 132, 138 + i * 14, 200), 190, 310, fill=(135, 165, 178), width=2)
    clean = clean.filter(ImageFilter.GaussianBlur(0.6))
    noisy = np.clip(
        np.asarray(clean, dtype=np.float32)
        + rng.normal(0, 34, (clean.height, clean.width, 1))
        + rng.normal(0, 26, (clean.height, clean.width, 3)),
        0,
        255,
    ).astype(np.uint8)
    image = Image.fromarray(noisy, "RGB")

    def conservative_nafnet(rgb: np.ndarray) -> np.ndarray:
        return rgb

    monkeypatch.setattr(denoise, "_run_nafnet", conservative_nafnet)

    result = denoise.denoise(image, DenoiseStrength.HEAVY)
    dark_background = (0, 0, 64, 80)
    subject = (68, 38, 190, 205)

    assert _mean_squared_error(result, clean, dark_background) < _mean_squared_error(image, clean, dark_background) * 0.86
    assert _mean_squared_error(result, clean, subject) < _mean_squared_error(image, clean, subject) * 0.9
    assert _luma_contrast(result, (88, 50, 96, 86), (118, 70, 132, 105)) > 45


def test_denoise_detail_restore_adds_sharpness_after_heavy_denoise() -> None:
    image = Image.new("RGB", (80, 80), (32, 32, 32))
    draw = ImageDraw.Draw(image)
    draw.rectangle((28, 12, 52, 68), fill=(210, 210, 210))
    blurred = image.filter(ImageFilter.GaussianBlur(radius=1.5))

    restored = photo_processor._restore_detail_after_denoise(blurred, DenoiseStrength.HEAVY)

    assert _edge_mean(restored) > _edge_mean(blurred) * 1.25


def test_denoise_detail_restore_respects_medium_and_none_strengths() -> None:
    image = Image.new("RGB", (80, 80), (32, 32, 32))
    draw = ImageDraw.Draw(image)
    draw.rectangle((28, 12, 52, 68), fill=(210, 210, 210))
    blurred = image.filter(ImageFilter.GaussianBlur(radius=1.5))

    medium = photo_processor._restore_detail_after_denoise(blurred, DenoiseStrength.MEDIUM)
    none = photo_processor._restore_detail_after_denoise(blurred, DenoiseStrength.NONE)

    assert _difference_sum(blurred, medium) == 0
    assert _difference_sum(blurred, none) == 0


def test_google_drive_confirm_params_parse_download_form() -> None:
    html = """
    <html><body><form action="/download">
      <input type="hidden" name="id" value="model-file-id">
      <input type="hidden" name="export" value="download">
      <input type="hidden" name="confirm" value="t">
      <input type="hidden" name="uuid" value="abc-123">
    </form></body></html>
    """

    params = denoise._google_drive_confirm_params(html)

    assert params == {
        "id": "model-file-id",
        "export": "download",
        "confirm": "t",
        "uuid": "abc-123",
    }


def test_google_drive_download_writes_direct_response(monkeypatch, tmp_path) -> None:
    opener = _FakeOpener([_FakeHttpResponse(b"weights", "application/octet-stream")])
    monkeypatch.setattr(denoise.urllib.request, "build_opener", lambda *_: opener)
    target = tmp_path / "model.pth"

    denoise._download_google_drive_file(denoise.NAFNET_WEIGHTS_URL, target)

    assert opener.urls == [denoise.NAFNET_WEIGHTS_URL]
    assert target.read_bytes() == b"weights"


def test_google_drive_download_follows_confirmation_form(monkeypatch, tmp_path) -> None:
    html = b"""
    <html><body><form action="/download">
      <input type="hidden" name="id" value="model-file-id">
      <input type="hidden" name="export" value="download">
      <input type="hidden" name="confirm" value="t">
      <input type="hidden" name="uuid" value="abc-123">
    </form></body></html>
    """
    opener = _FakeOpener(
        [
            _FakeHttpResponse(html, "text/html; charset=utf-8"),
            _FakeHttpResponse(b"weights", "application/octet-stream"),
        ]
    )
    monkeypatch.setattr(denoise.urllib.request, "build_opener", lambda *_: opener)
    target = tmp_path / "model.pth"

    denoise._download_google_drive_file("https://drive.google.com/uc?id=model-file-id", target)

    assert opener.urls[1].startswith("https://drive.usercontent.google.com/download?")
    assert "confirm=t" in opener.urls[1]
    assert target.read_bytes() == b"weights"


def test_vertical_perspective_estimator_detects_converging_architecture_lines() -> None:
    image = Image.new("RGB", (220, 180), (10, 10, 10))
    draw = ImageDraw.Draw(image)
    for offset in (0, 16, 32):
        draw.line((40 + offset, 170, 82 + offset, 12), fill=(245, 245, 245), width=3)
        draw.line((180 - offset, 170, 138 - offset, 12), fill=(245, 245, 245), width=3)

    inset = lens_distort._estimate_vertical_perspective_inset(np.asarray(image))

    assert inset > 8


def test_vertical_perspective_estimator_ignores_straight_vertical_lines() -> None:
    image = Image.new("RGB", (220, 180), (10, 10, 10))
    draw = ImageDraw.Draw(image)
    for x in (42, 74, 146, 178):
        draw.line((x, 12, x, 170), fill=(245, 245, 245), width=3)

    inset = lens_distort._estimate_vertical_perspective_inset(np.asarray(image))

    assert inset == 0


def test_vertical_perspective_correction_preserves_size_and_changes_pixels() -> None:
    image = Image.new("RGB", (120, 90), (20, 20, 20))
    draw = ImageDraw.Draw(image)
    draw.rectangle((30, 12, 90, 82), outline=(240, 240, 240), width=3)

    corrected = lens_distort._correct_vertical_perspective(np.asarray(image), inset=14)

    assert corrected.shape == (90, 120, 3)
    assert _difference_sum(image, Image.fromarray(corrected)) > 1000


def test_vertical_perspective_correction_noops_for_zero_inset() -> None:
    rgb = np.asarray(Image.new("RGB", (32, 24), (20, 40, 60)))

    corrected = lens_distort._correct_vertical_perspective(rgb, inset=0)

    assert np.array_equal(corrected, rgb)
