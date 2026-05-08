from io import BytesIO

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageStat

from models.enums import ColorGradePreset, DenoiseStrength
from services import adjustments, color_grade, denoise


def _mean_channel_delta(image: Image.Image, left: int, right: int) -> float:
    mean = ImageStat.Stat(image.convert("RGB")).mean
    return mean[left] - mean[right]


def _difference_sum(left: Image.Image, right: Image.Image) -> float:
    return sum(ImageStat.Stat(ImageChops.difference(left, right)).sum)


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
