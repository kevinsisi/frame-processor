from io import BytesIO

import numpy as np
from PIL import Image, ImageStat

from models.enums import ColorGradePreset, DenoiseStrength
from services import adjustments, color_grade, denoise


def _mean_channel_delta(image: Image.Image, left: int, right: int) -> float:
    mean = ImageStat.Stat(image.convert("RGB")).mean
    return mean[left] - mean[right]


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
