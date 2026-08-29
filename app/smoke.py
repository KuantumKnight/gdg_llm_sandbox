"""Dependency-free deployment health probe."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


def probe(url: str, *, attempts: int, delay_seconds: float) -> bool:
    for attempt in range(attempts):
        try:
            with urlopen(url, timeout=3) as response:
                payload = json.loads(response.read())
                if response.status == 200 and payload.get("status") in {"live", "ready"}:
                    return True
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
            pass
        if attempt + 1 < attempts:
            time.sleep(delay_seconds)
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "base_url",
        nargs="?",
        default=os.environ.get("SMOKE_BASE_URL", "http://127.0.0.1:8000"),
    )
    parser.add_argument("--path", default="/health/ready")
    parser.add_argument("--attempts", type=int, default=10)
    parser.add_argument("--delay-seconds", type=float, default=1.0)
    args = parser.parse_args()
    url = f"{args.base_url.rstrip('/')}/{args.path.lstrip('/')}"
    if probe(url, attempts=max(1, args.attempts), delay_seconds=max(0, args.delay_seconds)):
        sys.stdout.write(f"smoke check passed: {url}\n")
        return 0
    sys.stderr.write(f"smoke check failed: {url}\n")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
