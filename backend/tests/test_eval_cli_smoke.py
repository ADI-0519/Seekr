from __future__ import annotations

from pathlib import Path

import pytest
from app.evaluation.cli import build_parser, main
from app.evaluation.data_loader import (
    get_default_retrieval_path,
    get_default_segmentation_path,
)

_fixtures_available = pytest.mark.skipif(
    not get_default_retrieval_path().exists(),
    reason="gold fixtures not downloaded -- run: python scripts/download_artifacts.py --eval",
)


class TestCliSmoke:
    def test_dry_run_default_args(self) -> None:
        main(["--dry-run"])

    def test_dry_run_custom_output_dir(self, tmp_path: Path) -> None:
        main(["--dry-run", "--output-dir", str(tmp_path / "eval_out")])

    def test_dry_run_custom_seed(self) -> None:
        main(["--dry-run", "--seed", "123"])

    def test_dry_run_custom_k_values(self) -> None:
        main(["--dry-run", "--k-values", "1,5,20"])

    def test_dry_run_subset_ablations(self) -> None:
        main(["--dry-run", "--ablations", "baseline,+OCR"])

    def test_parser_help_text(self) -> None:
        parser = build_parser()
        help_text = parser.format_help()
        assert "--dry-run" in help_text
        assert "--seed" in help_text
        assert "--output-dir" in help_text

    def test_dry_run_with_finetune_task_id(self) -> None:
        main(["--dry-run", "--finetune-task-id", "abc123"])

    def test_finetune_task_id_in_help(self) -> None:
        parser = build_parser()
        assert "--finetune-task-id" in parser.format_help()

    @_fixtures_available
    def test_fixtures_exist(self) -> None:
        assert get_default_retrieval_path().exists()
        assert get_default_segmentation_path().exists()
