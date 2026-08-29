"""Fail CI when tracked files resemble common live credential formats."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

PATTERNS = {
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"),
    "GitHub token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b"),
    "OpenAI-style key": re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b"),
    "AWS access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "credentialed URL": re.compile(r"\b(?:redis|rediss|https?)://[^\s/:@]+:[^\s/@]+@"),
}
TEXT_SUFFIXES = {
    "",
    ".ini",
    ".json",
    ".md",
    ".py",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}


def tracked_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files"],
        check=True,
        capture_output=True,
        text=True,
    )
    return [Path(line) for line in result.stdout.splitlines() if line]


def main() -> int:
    findings: list[str] = []
    for path in tracked_files():
        if path.name == ".env" or path.suffix not in TEXT_SUFFIXES:
            if path.name == ".env":
                findings.append("tracked .env file")
            continue
        content = path.read_text(encoding="utf-8", errors="ignore")
        for label, pattern in PATTERNS.items():
            if pattern.search(content):
                findings.append(f"{path}: possible {label}")
    if findings:
        sys.stderr.write("\n".join(findings) + "\n")
        return 1
    sys.stdout.write("tracked-file secret scan passed\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
