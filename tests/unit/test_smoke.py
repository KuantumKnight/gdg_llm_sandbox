from __future__ import annotations

from types import TracebackType
from urllib.error import URLError

from app import smoke


class FakeResponse:
    status = 200

    def __init__(self, payload: bytes) -> None:
        self.payload = payload

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        del exc_type, exc_value, traceback

    def read(self) -> bytes:
        return self.payload


def test_probe_accepts_ready_health_payload(monkeypatch) -> None:
    monkeypatch.setattr(smoke, "urlopen", lambda url, timeout: FakeResponse(b'{"status":"ready"}'))

    assert smoke.probe("http://service/health/ready", attempts=1, delay_seconds=0)


def test_probe_retries_bounded_transport_failures(monkeypatch) -> None:
    calls = 0

    def unavailable(url: str, timeout: int) -> FakeResponse:
        nonlocal calls
        del url, timeout
        calls += 1
        raise URLError("offline")

    monkeypatch.setattr(smoke, "urlopen", unavailable)
    monkeypatch.setattr(smoke.time, "sleep", lambda delay: None)

    assert not smoke.probe("http://service/health/ready", attempts=3, delay_seconds=0)
    assert calls == 3
