from io import BytesIO

from PIL import Image, ImageStat

from services import adjustments


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
