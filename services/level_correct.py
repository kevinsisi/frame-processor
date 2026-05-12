"""水平校正：用 Gemini Vision 分析照片回報需要旋轉的角度。

策略：
1. 把照片縮成 long-edge 768px 的 JPEG（節省 token）送給 Gemini
2. Prompt：要求回傳「順時針旋轉幾度才會把地平線轉到水平」，限制 -90 ~ 90，回傳純數字
3. 解析數字 → ``cv2.warpAffine`` 旋轉（無上限，30° 就轉 30°）
4. 旋轉後用反推內接矩形裁掉黑邊
5. Gemini API key 缺失或回應無法解析時 raise，讓 worker 標 fail（不靜默 fallback）

錯誤分類與重試（``_classify_gemini_error`` / ``_backoff_seconds``）：
- AUTH（401 / 403）：不重試，直接 fail；換 key 才可能解
- QUOTA（429）：長 backoff 15 → 30 → 60s 共 3 次
- TIMEOUT（DeadlineExceeded / RetryError）：中 backoff 2 → 4 → 8s
- TRANSIENT（503 / 500 / Aborted）：短 backoff 1 → 2 → 4s
- PERMANENT / 其它：短 backoff 0.5s 一次後 fail

公開介面：``correct_level(image: PIL.Image) -> tuple[PIL.Image, float]``
"""

from __future__ import annotations

import io
import re
import time
from enum import Enum

import cv2
import numpy as np
from PIL import Image

from api.config import settings

_PROMPT = (
    "Look at this photo. Estimate how many degrees the photo needs to be rotated "
    "(positive = counter-clockwise) so that the natural horizon line — the ground "
    "line, the floor edge, or the long horizontal lines of vehicles or buildings — "
    "becomes perfectly horizontal. Return ONLY a single number between -90 and 90 "
    "with no units, no explanation, no extra text. If the photo is already level, "
    "return 0."
)

_NUMBER_RE = re.compile(r"-?\d+(?:\.\d+)?")

# Per-call timeout (秒) — Gemini Flash 處理 768px 圖通常 1-3s，30s 已留足容錯
GEMINI_REQUEST_TIMEOUT_SECONDS = 30

# 重試上限
GEMINI_MAX_ATTEMPTS = 3


class LevelCorrectError(RuntimeError):
    pass


class GeminiErrorKind(str, Enum):
    """Gemini API 錯誤分類，用來決定 retry 策略。"""

    AUTH = "auth"
    QUOTA = "quota"
    TIMEOUT = "timeout"
    TRANSIENT = "transient"
    PERMANENT = "permanent"


def correct_level(image: Image.Image) -> tuple[Image.Image, float]:
    angle_deg = _ask_gemini_for_angle(image)
    if abs(angle_deg) < 0.2:
        return image, 0.0
    rgb = np.array(image.convert("RGB"))
    rotated = _rotate_and_crop_black_borders(rgb, angle_deg)
    return Image.fromarray(rotated), angle_deg


def _classify_gemini_error(exc: BaseException) -> GeminiErrorKind:
    """Map an SDK / network exception to a retry category.

    Compare by class name string so we don't need the SDK installed at import time
    and tests can use lightweight fakes.
    """
    name = type(exc).__name__
    if name in {"Unauthenticated", "PermissionDenied", "Forbidden"}:
        return GeminiErrorKind.AUTH
    if name in {"ResourceExhausted", "TooManyRequests"}:
        return GeminiErrorKind.QUOTA
    if name in {"DeadlineExceeded", "RetryError", "TimeoutError"}:
        return GeminiErrorKind.TIMEOUT
    if name in {
        "ServiceUnavailable",
        "InternalServerError",
        "Aborted",
        "Cancelled",
        "GatewayTimeout",
    }:
        return GeminiErrorKind.TRANSIENT
    return GeminiErrorKind.PERMANENT


def _backoff_seconds(kind: GeminiErrorKind, attempt: int) -> float | None:
    """How long to sleep before the next attempt, or ``None`` to stop retrying.

    ``attempt`` is 0-indexed for the attempt that *just failed*. Returning
    ``None`` means do not retry further.
    """
    if kind is GeminiErrorKind.AUTH:
        return None
    if attempt >= GEMINI_MAX_ATTEMPTS - 1:
        return None
    if kind is GeminiErrorKind.QUOTA:
        return 15.0 * (2 ** attempt)
    if kind is GeminiErrorKind.TIMEOUT:
        return 2.0 * (2 ** attempt)
    if kind is GeminiErrorKind.TRANSIENT:
        return 1.0 * (2 ** attempt)
    return 0.5


def _format_failure_message(kind: GeminiErrorKind, exc: BaseException, attempts: int) -> str:
    label = kind.value
    return f"Gemini level_correct failed ({label}) after {attempts} attempt(s): {type(exc).__name__}: {exc}"


def _ask_gemini_for_angle(image: Image.Image) -> float:
    api_key = _active_gemini_api_key()
    if not api_key:
        raise LevelCorrectError(
            "GEMINI_API_KEY not configured; level_correct requires Gemini Vision"
        )

    import google.generativeai as genai  # type: ignore

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(settings.gemini_model)

    payload = _downscale_for_vision(image)
    return _call_gemini_with_retry(
        lambda: _generate_angle(model, payload),
        sleep=time.sleep,
    )


def _generate_angle(model, payload: bytes) -> float:
    """Single Gemini call. Raises ``LevelCorrectError`` for non-retryable parse failures."""
    response = model.generate_content(
        [
            {"mime_type": "image/jpeg", "data": payload},
            _PROMPT,
        ],
        request_options={"timeout": GEMINI_REQUEST_TIMEOUT_SECONDS},
    )
    text = (response.text or "").strip()
    match = _NUMBER_RE.search(text)
    if not match:
        raise LevelCorrectError(f"Gemini returned non-numeric angle: {text!r}")
    angle = float(match.group(0))
    if angle < -90 or angle > 90:
        raise LevelCorrectError(f"Gemini angle out of range: {angle}")
    return angle


def _call_gemini_with_retry(call, *, sleep=time.sleep) -> float:
    """Retry ``call()`` per the GeminiErrorKind backoff schedule.

    ``call`` must return ``float`` on success or raise. ``LevelCorrectError``
    raised by ``call`` is treated as a deterministic parse failure and not
    retried.
    """
    last_exc: BaseException | None = None
    last_kind: GeminiErrorKind = GeminiErrorKind.PERMANENT
    for attempt in range(GEMINI_MAX_ATTEMPTS):
        try:
            return call()
        except LevelCorrectError:
            raise
        except Exception as exc:
            kind = _classify_gemini_error(exc)
            last_exc = exc
            last_kind = kind
            wait = _backoff_seconds(kind, attempt)
            if wait is None:
                break
            sleep(wait)
    assert last_exc is not None
    raise LevelCorrectError(
        _format_failure_message(last_kind, last_exc, attempt + 1)
    ) from last_exc


def _active_gemini_api_key() -> str | None:
    from api.database import SessionLocal
    from services.settings_store import get_active_gemini_api_key

    with SessionLocal() as db:
        return get_active_gemini_api_key(db)


def _downscale_for_vision(image: Image.Image, max_edge: int = 768) -> bytes:
    rgb = image.convert("RGB")
    w, h = rgb.size
    scale = max_edge / max(w, h)
    if scale < 1.0:
        rgb = rgb.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    buf = io.BytesIO()
    rgb.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


def _rotate_and_crop_black_borders(rgb: np.ndarray, angle_deg: float) -> np.ndarray:
    h, w = rgb.shape[:2]
    center = (w / 2.0, h / 2.0)
    matrix = cv2.getRotationMatrix2D(center, angle_deg, 1.0)
    rotated = cv2.warpAffine(
        rgb, matrix, (w, h), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REPLICATE
    )
    inset_w, inset_h = _inscribed_rect(w, h, angle_deg)
    if inset_w <= 0 or inset_h <= 0:
        return rotated
    x0 = (w - inset_w) // 2
    y0 = (h - inset_h) // 2
    return rotated[y0 : y0 + inset_h, x0 : x0 + inset_w]


def _inscribed_rect(w: int, h: int, angle_deg: float) -> tuple[int, int]:
    """旋轉後保留同 aspect ratio 的最大內接矩形。"""
    angle = abs(np.radians(angle_deg))
    if angle <= 1e-6:
        return w, h
    cos_a = np.cos(angle)
    sin_a = np.sin(angle)
    if w <= h:
        long_side, short_side = h, w
    else:
        long_side, short_side = w, h
    if short_side <= 2.0 * sin_a * cos_a * long_side or abs(sin_a - cos_a) < 1e-9:
        x = 0.5 * short_side
        if w >= h:
            wr, hr = x / sin_a, x / cos_a
        else:
            wr, hr = x / cos_a, x / sin_a
    else:
        cos_2a = cos_a * cos_a - sin_a * sin_a
        wr = (w * cos_a - h * sin_a) / cos_2a
        hr = (h * cos_a - w * sin_a) / cos_2a
    return max(int(wr), 1), max(int(hr), 1)
