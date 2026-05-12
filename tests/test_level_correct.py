"""Unit tests for the Gemini retry / categorization logic in level_correct.

These tests exercise the pure-function retry layer (``_call_gemini_with_retry``
+ ``_classify_gemini_error`` + ``_backoff_seconds``) without touching the actual
Gemini SDK or network. They DO NOT cover the full ``correct_level`` path; the
geometric rotation half is left to integration smoke tests.
"""

from __future__ import annotations

import pytest

from services.level_correct import (
    GEMINI_MAX_ATTEMPTS,
    GeminiErrorKind,
    LevelCorrectError,
    _backoff_seconds,
    _call_gemini_with_retry,
    _classify_gemini_error,
    _generate_angle,
)


class ResourceExhausted(Exception):
    pass


class DeadlineExceeded(Exception):
    pass


class Unauthenticated(Exception):
    pass


class PermissionDenied(Exception):
    pass


class ServiceUnavailable(Exception):
    pass


class InternalServerError(Exception):
    pass


class InvalidArgument(Exception):
    pass


class FakeResponse:
    def __init__(self, text: str) -> None:
        self.text = text


class FakeAngleModel:
    def __init__(self, text: str) -> None:
        self.text = text

    def generate_content(self, *_args, **_kwargs) -> FakeResponse:
        return FakeResponse(self.text)


def test_classify_quota_errors() -> None:
    assert _classify_gemini_error(ResourceExhausted("429")) is GeminiErrorKind.QUOTA


def test_classify_timeout_errors() -> None:
    assert _classify_gemini_error(DeadlineExceeded("slow")) is GeminiErrorKind.TIMEOUT
    assert _classify_gemini_error(TimeoutError("slow")) is GeminiErrorKind.TIMEOUT


def test_classify_auth_errors() -> None:
    assert _classify_gemini_error(Unauthenticated("bad key")) is GeminiErrorKind.AUTH
    assert _classify_gemini_error(PermissionDenied("no scope")) is GeminiErrorKind.AUTH


def test_classify_transient_errors() -> None:
    assert _classify_gemini_error(ServiceUnavailable("503")) is GeminiErrorKind.TRANSIENT
    assert _classify_gemini_error(InternalServerError("500")) is GeminiErrorKind.TRANSIENT


def test_classify_permanent_unknown_errors_fall_through() -> None:
    assert _classify_gemini_error(InvalidArgument("400")) is GeminiErrorKind.PERMANENT
    assert _classify_gemini_error(ValueError("misc")) is GeminiErrorKind.PERMANENT


def test_backoff_quota_uses_long_delays() -> None:
    assert _backoff_seconds(GeminiErrorKind.QUOTA, 0) == 15.0
    assert _backoff_seconds(GeminiErrorKind.QUOTA, 1) == 30.0
    # On the final allowed attempt (GEMINI_MAX_ATTEMPTS - 1) we stop retrying.
    assert _backoff_seconds(GeminiErrorKind.QUOTA, GEMINI_MAX_ATTEMPTS - 1) is None


def test_backoff_timeout_uses_medium_delays() -> None:
    assert _backoff_seconds(GeminiErrorKind.TIMEOUT, 0) == 2.0
    assert _backoff_seconds(GeminiErrorKind.TIMEOUT, 1) == 4.0


def test_backoff_transient_uses_short_delays() -> None:
    assert _backoff_seconds(GeminiErrorKind.TRANSIENT, 0) == 1.0
    assert _backoff_seconds(GeminiErrorKind.TRANSIENT, 1) == 2.0


def test_backoff_auth_never_retries() -> None:
    assert _backoff_seconds(GeminiErrorKind.AUTH, 0) is None
    assert _backoff_seconds(GeminiErrorKind.AUTH, 1) is None


def test_backoff_permanent_retries_once_then_stops() -> None:
    assert _backoff_seconds(GeminiErrorKind.PERMANENT, 0) == 0.5
    assert _backoff_seconds(GeminiErrorKind.PERMANENT, GEMINI_MAX_ATTEMPTS - 1) is None


def test_retry_succeeds_on_first_call_no_sleep() -> None:
    sleeps: list[float] = []

    result = _call_gemini_with_retry(lambda: 12.5, sleep=sleeps.append)

    assert result == 12.5
    assert sleeps == []


def test_retry_recovers_after_transient_then_succeeds() -> None:
    attempts = {"n": 0}
    sleeps: list[float] = []

    def call() -> float:
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise ServiceUnavailable("503")
        return 3.0

    result = _call_gemini_with_retry(call, sleep=sleeps.append)

    assert result == 3.0
    assert attempts["n"] == 2
    assert sleeps == [1.0]


def test_retry_exhausts_quota_attempts_and_wraps_error() -> None:
    sleeps: list[float] = []

    def call() -> float:
        raise ResourceExhausted("429 too many")

    with pytest.raises(LevelCorrectError) as exc_info:
        _call_gemini_with_retry(call, sleep=sleeps.append)

    message = str(exc_info.value)
    assert "quota" in message
    assert "ResourceExhausted" in message
    assert f"after {GEMINI_MAX_ATTEMPTS}" in message
    # Quota uses 15s, 30s before exhausting; final attempt has no sleep after it.
    assert sleeps == [15.0, 30.0]


def test_retry_does_not_sleep_for_auth_errors() -> None:
    sleeps: list[float] = []

    def call() -> float:
        raise Unauthenticated("bad key")

    with pytest.raises(LevelCorrectError) as exc_info:
        _call_gemini_with_retry(call, sleep=sleeps.append)

    assert sleeps == []
    assert "auth" in str(exc_info.value)


def test_retry_propagates_level_correct_error_without_retry() -> None:
    """Deterministic parse failures inside the call must not be retried."""
    attempts = {"n": 0}
    sleeps: list[float] = []

    def call() -> float:
        attempts["n"] += 1
        raise LevelCorrectError("Gemini returned non-numeric angle: 'oops'")

    with pytest.raises(LevelCorrectError, match="non-numeric"):
        _call_gemini_with_retry(call, sleep=sleeps.append)

    assert attempts["n"] == 1
    assert sleeps == []


def test_retry_timeout_then_quota_uses_kind_specific_backoff() -> None:
    """Backoff is chosen based on the error of each individual attempt."""
    attempts = {"n": 0}
    sleeps: list[float] = []

    def call() -> float:
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise DeadlineExceeded("slow")
        raise ResourceExhausted("429")

    with pytest.raises(LevelCorrectError) as exc_info:
        _call_gemini_with_retry(call, sleep=sleeps.append)

    # attempt 0: timeout → 2.0; attempt 1: quota → 30.0; attempt 2: quota → stop.
    assert sleeps == [2.0, 30.0]
    assert "quota" in str(exc_info.value)


def test_generate_angle_skips_out_of_range_gemini_response() -> None:
    assert _generate_angle(FakeAngleModel("260.0"), b"jpeg") == 0.0


def test_generate_angle_still_fails_for_non_numeric_response() -> None:
    with pytest.raises(LevelCorrectError, match="non-numeric"):
        _generate_angle(FakeAngleModel("not sure"), b"jpeg")
