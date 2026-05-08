from __future__ import annotations

from io import BytesIO
from typing import Any

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

from models.enums import ColorGradePreset
from services import color_grade


def normalize_params(params: dict[str, Any] | None) -> dict[str, Any]:
    params = params or {}
    legacy_distortion = _bounded_float(params.get("distortion"), -100.0, 100.0)
    distortion_x = _bounded_float(params.get("distortion_x"), -100.0, 100.0)
    if legacy_distortion and not distortion_x:
        distortion_x = legacy_distortion
    return {
        "exposure": _bounded_float(params.get("exposure"), -5.0, 5.0),
        "contrast": _bounded_float(params.get("contrast"), -100.0, 100.0),
        "highlights": _bounded_float(params.get("highlights"), -100.0, 100.0),
        "shadows": _bounded_float(params.get("shadows"), -100.0, 100.0),
        "temperature": _bounded_float(params.get("temperature"), -100.0, 100.0),
        "tint": _bounded_float(params.get("tint"), -100.0, 100.0),
        "saturation": _bounded_float(params.get("saturation"), -100.0, 100.0),
        "vibrance": _bounded_float(params.get("vibrance"), -100.0, 100.0),
        "clarity": _bounded_float(params.get("clarity"), -100.0, 100.0),
        "sharpness": _bounded_float(params.get("sharpness"), -100.0, 100.0),
        "orientation": _normalized_orientation(params.get("orientation")),
        "rotation": _bounded_float(params.get("rotation"), -45.0, 45.0),
        "crop_zoom": _bounded_float(params.get("crop_zoom"), 1.0, 3.0),
        "crop_x": _bounded_float(params.get("crop_x"), -100.0, 100.0),
        "crop_y": _bounded_float(params.get("crop_y"), -100.0, 100.0),
        "distortion": distortion_x,
        "distortion_x": distortion_x,
        "distortion_y": _bounded_float(params.get("distortion_y"), -100.0, 100.0),
        "grade_preset": _normalized_grade_preset(params.get("grade_preset")),
        "hsl": _normalize_hsl(params.get("hsl")),
    }


def apply_adjustments(image: Image.Image, params: dict[str, Any]) -> Image.Image:
    p = normalize_params(params)
    img = image.convert("RGB")
    img = _orientation(img, p["orientation"])
    img = _geometry(img, p)
    if p["grade_preset"]:
        img = color_grade.apply_grade(img, ColorGradePreset(p["grade_preset"]))
    img = _temperature_tint(img, p["temperature"], p["tint"])
    if p["exposure"]:
        img = ImageEnhance.Brightness(img).enhance(2 ** p["exposure"])
    if p["contrast"]:
        img = ImageEnhance.Contrast(img).enhance(1 + p["contrast"] / 100)
    img = _highlights_shadows(img, p["highlights"], p["shadows"])
    if p["saturation"]:
        img = ImageEnhance.Color(img).enhance(max(0.0, 1 + p["saturation"] / 100))
    img = _vibrance(img, p["vibrance"])
    img = _hsl(img, p["hsl"])
    img = _clarity(img, p["clarity"])
    img = _sharpness(img, p["sharpness"])
    return img


def _orientation(image: Image.Image, degrees: int) -> Image.Image:
    if degrees == 90:
        return image.transpose(Image.Transpose.ROTATE_270)
    if degrees == 180:
        return image.transpose(Image.Transpose.ROTATE_180)
    if degrees == 270:
        return image.transpose(Image.Transpose.ROTATE_90)
    return image


def _geometry(image: Image.Image, params: dict[str, Any]) -> Image.Image:
    img = image
    if params["distortion_x"] or params["distortion_y"]:
        img = _manual_distortion(img, params["distortion_x"], params["distortion_y"])
    if params["rotation"]:
        img = img.rotate(
            params["rotation"],
            resample=Image.Resampling.BICUBIC,
            expand=True,
            fillcolor=(0, 0, 0),
        )
    if params["crop_zoom"] != 1.0 or params["crop_x"] or params["crop_y"]:
        img = _manual_crop(img, params["crop_zoom"], params["crop_x"], params["crop_y"])
    return img


def _manual_crop(image: Image.Image, zoom: float, offset_x: float, offset_y: float) -> Image.Image:
    w, h = image.size
    crop_w = max(1, round(w / zoom))
    crop_h = max(1, round(h / zoom))
    max_x = max(0, w - crop_w)
    max_y = max(0, h - crop_h)
    left = round((max_x / 2) + (offset_x / 100) * (max_x / 2))
    top = round((max_y / 2) + (offset_y / 100) * (max_y / 2))
    left = max(0, min(max_x, left))
    top = max(0, min(max_y, top))
    return image.crop((left, top, left + crop_w, top + crop_h)).resize(
        (w, h), Image.Resampling.LANCZOS
    )


def _manual_distortion(image: Image.Image, horizontal: float, vertical: float) -> Image.Image:
    # X-axis correction preserves the legacy single `distortion` trapezoid behavior.
    w, h = image.size
    x_shift = (horizontal / 100) * w * 0.08
    y_shift = (vertical / 100) * h * 0.08
    coeffs = _perspective_coeffs(
        [(0, 0), (w, 0), (w, h), (0, h)],
        [
            (-x_shift, y_shift),
            (w + x_shift, -y_shift),
            (w - x_shift, h + y_shift),
            (x_shift, h - y_shift),
        ],
    )
    return image.transform(
        (w, h),
        Image.Transform.PERSPECTIVE,
        coeffs,
        resample=Image.Resampling.BICUBIC,
        fillcolor=(0, 0, 0),
    )


def _perspective_coeffs(source: list[tuple[float, float]], target: list[tuple[float, float]]) -> list[float]:
    import numpy as np

    matrix = []
    for (x, y), (u, v) in zip(target, source, strict=True):
        matrix.append([x, y, 1, 0, 0, 0, -u * x, -u * y])
        matrix.append([0, 0, 0, x, y, 1, -v * x, -v * y])
    a = np.asarray(matrix, dtype=float)
    b = np.asarray(source, dtype=float).reshape(8)
    return np.linalg.solve(a, b).tolist()


def preview_jpeg(image: Image.Image, params: dict[str, Any], *, long_edge: int = 760) -> bytes:
    try:
        image.draft("RGB", (long_edge, long_edge))
    except (AttributeError, OSError):
        pass
    img = ImageOps.exif_transpose(image).convert("RGB")
    img.thumbnail((long_edge, long_edge), Image.Resampling.LANCZOS)
    img = apply_adjustments(img, params)
    img.thumbnail((long_edge, long_edge), Image.Resampling.LANCZOS)
    out = BytesIO()
    img.save(out, format="JPEG", quality=88, optimize=True)
    return out.getvalue()


def _normalize_hsl(value: Any) -> dict[str, dict[str, float]]:
    colors = ("red", "orange", "yellow", "green", "blue", "purple")
    source = value if isinstance(value, dict) else {}
    return {
        color: {
            "hue": _bounded_float((source.get(color) or {}).get("hue"), -100.0, 100.0),
            "saturation": _bounded_float(
                (source.get(color) or {}).get("saturation"), -100.0, 100.0
            ),
            "luminance": _bounded_float(
                (source.get(color) or {}).get("luminance"), -100.0, 100.0
            ),
        }
        for color in colors
    }


def _temperature_tint(image: Image.Image, temperature: float, tint: float) -> Image.Image:
    r, g, b = image.split()
    r_delta = temperature * 0.42 + tint * 0.14
    g_delta = -tint * 0.24
    b_delta = -temperature * 0.42 + tint * 0.14
    return Image.merge(
        "RGB",
        (
            r.point(lambda v: _clamp(v + r_delta)),
            g.point(lambda v: _clamp(v + g_delta)),
            b.point(lambda v: _clamp(v + b_delta)),
        ),
    )


def _highlights_shadows(image: Image.Image, highlights: float, shadows: float) -> Image.Image:
    if not highlights and not shadows:
        return image
    lut: list[int] = []
    for i in range(256):
        x = i / 255
        shadow_weight = max(0.0, 1.0 - x * 2)
        highlight_weight = max(0.0, x * 2 - 1.0)
        delta = shadows * shadow_weight * 0.85 + highlights * highlight_weight * 0.85
        lut.append(_clamp(i + delta))
    return image.point(lut * 3)


def _hsl(image: Image.Image, hsl: dict[str, dict[str, float]]) -> Image.Image:
    hsv = image.convert("HSV")
    pixels = bytearray(hsv.tobytes())
    for i in range(0, len(pixels), 3):
        hue = pixels[i] / 255 * 360
        color = _hue_bucket(hue)
        if color is None:
            continue
        adj = hsl[color]
        pixels[i] = int((pixels[i] + adj["hue"] / 100 * 18) % 256)
        pixels[i + 1] = _clamp(pixels[i + 1] * max(0.0, 1 + adj["saturation"] / 100))
        pixels[i + 2] = _clamp(pixels[i + 2] + adj["luminance"] * 1.2)
    return Image.frombytes("HSV", hsv.size, bytes(pixels)).convert("RGB")


def _vibrance(image: Image.Image, amount: float) -> Image.Image:
    if not amount:
        return image
    hsv = image.convert("HSV")
    pixels = bytearray(hsv.tobytes())
    for i in range(0, len(pixels), 3):
        saturation = pixels[i + 1]
        protection = 1.0 - saturation / 255
        pixels[i + 1] = _clamp(saturation + amount * protection * 1.25)
    return Image.frombytes("HSV", hsv.size, bytes(pixels)).convert("RGB")


def _clarity(image: Image.Image, amount: float) -> Image.Image:
    if not amount:
        return image
    radius = 18
    percent = int(abs(amount) * 1.2)
    if amount > 0:
        return image.filter(ImageFilter.UnsharpMask(radius=radius, percent=percent, threshold=8))
    blurred = image.filter(ImageFilter.GaussianBlur(radius=1.2))
    return Image.blend(image, blurred, min(0.65, abs(amount) / 150))


def _sharpness(image: Image.Image, amount: float) -> Image.Image:
    if not amount:
        return image
    factor = max(0.0, 1 + amount / 50)
    return ImageEnhance.Sharpness(image).enhance(factor)


def _hue_bucket(hue: float) -> str | None:
    if hue < 20 or hue >= 340:
        return "red"
    if hue < 50:
        return "orange"
    if hue < 80:
        return "yellow"
    if hue < 170:
        return "green"
    if hue < 260:
        return "blue"
    if hue < 340:
        return "purple"
    return None


def _bounded_float(value: Any, low: float, high: float) -> float:
    try:
        parsed = float(value or 0)
    except (TypeError, ValueError):
        parsed = 0.0
    return max(low, min(high, parsed))


def _normalized_orientation(value: Any) -> int:
    try:
        parsed = int(value or 0)
    except (TypeError, ValueError):
        parsed = 0
    return parsed % 360 if parsed % 90 == 0 else 0


def _normalized_grade_preset(value: Any) -> str | None:
    if value is None:
        return None
    try:
        return ColorGradePreset(str(value)).value
    except ValueError:
        return None


def _clamp(v: float) -> int:
    return max(0, min(255, round(v)))
