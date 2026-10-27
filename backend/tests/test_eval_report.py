from __future__ import annotations

import json
from pathlib import Path

import pytest
from app.evaluation.ablation import AblationConfig, AblationResult
from app.evaluation.cli import main
from app.evaluation.report import EvalReport, build_report


def make_config(name: str = "baseline") -> AblationConfig:
    return AblationConfig(
        name=name,
        include_slide_text=False,
        include_context_template=False,
        embedding_model="bge-m3",
        seed=42,
    )


def make_result(
    name: str = "baseline",
    recall_1: float = 0.7,
    mrr: float = 0.75,
    seg_f1: float = 0.8,
) -> AblationResult:
    return AblationResult(
        config=make_config(name),
        retrieval_metrics={
            "hit@1": recall_1,
            "hit@3": min(recall_1 + 0.05, 1.0),
            "hit@5": min(recall_1 + 0.10, 1.0),
            "hit@10": min(recall_1 + 0.15, 1.0),
            "mrr": mrr,
        },
        segmentation_metrics={"precision": seg_f1, "recall": seg_f1, "f1": seg_f1},
        query_type_breakdown={"_overall": {"hit@1": recall_1, "mrr": mrr}},
        timestamp="2026-01-01T00:00:00+00:00",
    )


def make_report(*names: str) -> EvalReport:
    results = [make_result(n) for n in names]
    return EvalReport(
        generated_at="2026-01-01T00:00:00+00:00",
        configs=[r.config for r in results],
        results=results,
    )


class TestToTable:
    def test_table_has_header_row(self) -> None:
        report = make_report("baseline", "+OCR")
        table = report.to_table()
        assert "Config" in table
        assert "Hit@1" in table
        assert "MRR" in table
        assert "Seg-F1" in table

    def test_table_has_correct_row_count(self) -> None:
        report = make_report("baseline", "+OCR", "+Context")
        lines = report.to_table().splitlines()
        # header + separator + one row per result
        pipe_lines = [ln for ln in lines if ln.startswith("|")]
        assert len(pipe_lines) == 2 + len(report.results)

    def test_table_with_missing_segmentation(self) -> None:
        result = AblationResult(
            config=make_config("baseline"),
            retrieval_metrics={"hit@1": 0.5, "mrr": 0.6},
            segmentation_metrics={},
            query_type_breakdown={},
            timestamp="2026-01-01T00:00:00+00:00",
        )
        report = EvalReport(
            generated_at="2026-01-01T00:00:00+00:00",
            configs=[result.config],
            results=[result],
        )
        table = report.to_table()
        assert "0.0000" in table

    def test_table_custom_k_values(self) -> None:
        report = make_report("baseline")
        table = report.to_table(k_values=[1, 20])
        assert "Hit@20" in table
        assert "Hit@1" in table


class TestToJson:
    def test_json_round_trip(self, tmp_path: Path) -> None:
        report = make_report("baseline", "+OCR")
        out = tmp_path / "out.json"
        report.to_json(out)
        data = json.loads(out.read_text(encoding="utf-8"))
        assert "generated_at" in data
        assert isinstance(data["results"], list)
        assert len(data["results"]) == 2

    def test_json_creates_parent_dirs(self, tmp_path: Path) -> None:
        report = make_report("baseline")
        out = tmp_path / "subdir" / "deep" / "out.json"
        report.to_json(out)
        assert out.exists()


class TestToMarkdown:
    def test_markdown_has_header(self, tmp_path: Path) -> None:
        report = make_report("baseline")
        dest = tmp_path / "report.md"
        report.to_markdown(dest)
        content = dest.read_text(encoding="utf-8")
        assert content.startswith("# Evaluation Report")

    def test_markdown_contains_table(self, tmp_path: Path) -> None:
        report = make_report("baseline", "+OCR")
        dest = tmp_path / "report.md"
        report.to_markdown(dest)
        content = dest.read_text(encoding="utf-8")
        assert "|" in content


class TestToPlots:
    def test_plots_creates_files(self, tmp_path: Path) -> None:
        pytest.importorskip("matplotlib")
        report = make_report("baseline", "+OCR")
        plots_dir = tmp_path / "plots"
        report.to_plots(plots_dir)
        pngs = list(plots_dir.glob("*.png"))
        assert len(pngs) >= 1

    def test_plots_returns_file_paths(self, tmp_path: Path) -> None:
        pytest.importorskip("matplotlib")
        report = make_report("baseline", "+OCR")
        paths = report.to_plots(tmp_path / "plots")
        assert all(p.endswith(".png") for p in paths)

    def test_plots_creates_output_dir(self, tmp_path: Path) -> None:
        pytest.importorskip("matplotlib")
        report = make_report("baseline", "+OCR")
        new_dir = tmp_path / "nonexistent" / "nested"
        assert not new_dir.exists()
        report.to_plots(new_dir)
        assert new_dir.exists()


class TestBuildReport:
    def test_build_report_sets_timestamp(self) -> None:
        results = [make_result("baseline"), make_result("+OCR")]
        report = build_report(results)
        assert isinstance(report.generated_at, str)
        assert len(report.generated_at) > 0

    def test_build_report_extracts_configs(self) -> None:
        results = [make_result("baseline"), make_result("+OCR"), make_result("+Context")]
        report = build_report(results)
        assert len(report.configs) == len(results)
        assert [c.name for c in report.configs] == ["baseline", "+OCR", "+Context"]


class TestCliDryRun:
    def test_dry_run_exits_cleanly(self) -> None:
        # --dry-run must return without touching services or the filesystem
        main(["--dry-run"])
