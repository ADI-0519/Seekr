#!/usr/bin/env python3
"""Reject common identifying or coursework-specific text in benchmark data."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Iterator

DEFAULT_PATHS = (
    Path("evaluation_output/sentences.json"),
    Path("app/evaluation/fixtures/retrieval_gold.json"),
    Path("app/evaluation/fixtures/segmentation_gold.json"),
)

_PROHIBITED_PATTERNS = {
    "named university": re.compile(
        r"\b(?:university\s+of\s+[a-z][a-z&' -]+|[a-z][a-z&' -]+\s+university|king'?s\s+college)\b",
        re.IGNORECASE,
    ),
    "UK module code": re.compile(r"\b\d[A-Z]{5,}\b"),
    "student identifier": re.compile(
        r"\b(?:student(?:\s+(?:id|number))?|candidate\s+number)\s*[:#-]?\s*\d{5,}\b",
        re.IGNORECASE,
    ),
    "academic email address": re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.ac\.uk\b", re.IGNORECASE),
    "coursework-specific term": re.compile(
        r"\b(?:coursework|dissertation|assignment\s+(?:brief|submission)|module\s+code)\b",
        re.IGNORECASE,
    ),
}


def _strings(value: object, location: str = "$") -> Iterator[tuple[str, str]]:
    if isinstance(value, str):
        yield location, value
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _strings(item, f"{location}[{index}]")
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from _strings(item, f"{location}.{key}")


def find_prohibited_content(path: Path) -> list[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    findings = []
    for location, text in _strings(data):
        for label, pattern in _PROHIBITED_PATTERNS.items():
            if pattern.search(text):
                findings.append(f"{path}:{location}: {label}")
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check benchmark JSON for common identifying and coursework-specific text."
    )
    parser.add_argument("paths", nargs="*", type=Path, default=list(DEFAULT_PATHS))
    args = parser.parse_args(argv)

    missing = [path for path in args.paths if not path.is_file()]
    if missing:
        parser.error(f"benchmark data not found: {', '.join(str(path) for path in missing)}")

    findings = [finding for path in args.paths for finding in find_prohibited_content(path)]
    if findings:
        print("Benchmark privacy check failed:")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    print(f"Benchmark privacy check passed for {len(args.paths)} files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
