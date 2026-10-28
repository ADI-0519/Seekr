from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.validate_benchmark_data import find_prohibited_content, main


def write_json(path: Path, value: object) -> Path:
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def test_allows_anonymised_benchmark_text(tmp_path: Path) -> None:
    path = write_json(tmp_path / "benchmark.json", {"query": "How does gradient descent work?"})

    assert find_prohibited_content(path) == []
    assert main([str(path)]) == 0


@pytest.mark.parametrize(
    "text",
    [
        "University of Example",
        "Example University",
        "Module code: 5CCSAGAP",
        "Student ID: 12345678",
        "person@example.ac.uk",
        "Coursework submission",
    ],
)
def test_rejects_identifying_or_coursework_text(tmp_path: Path, text: str) -> None:
    path = write_json(tmp_path / "benchmark.json", {"nested": [{"text": text}]})

    assert find_prohibited_content(path)
    assert main([str(path)]) == 1
