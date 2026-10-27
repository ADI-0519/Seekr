from __future__ import annotations

import dataclasses
import json
from pathlib import Path

from app.evaluation.ablation import AblationConfig, AblationResult

try:
    import matplotlib

    matplotlib.use("Agg")  # no GUI in headless environments
    import matplotlib.pyplot as plt

    _MPL_AVAILABLE = True
except ImportError:
    _MPL_AVAILABLE = False

_DEFAULT_K_VALUES: list[int] = [1, 3, 5, 10]
_MPL_MISSING = "matplotlib is not installed; run pip install matplotlib"


@dataclasses.dataclass
class EvalReport:
    generated_at: str
    configs: list[AblationConfig]
    results: list[AblationResult]

    def to_table(self, k_values: list[int] | None = None) -> str:
        resolved_k = k_values if k_values is not None else _DEFAULT_K_VALUES

        # build header
        col_config = 14
        col_metric = 10
        recall_headers = [f"Hit@{k}" for k in resolved_k]
        headers = ["Config"] + recall_headers + ["MRR", "Seg-F1"]
        widths = (
            [col_config]
            + [max(col_metric, len(h) + 2) for h in recall_headers]
            + [col_metric, col_metric]
        )

        header_row = "| " + " | ".join(h.ljust(w - 2) for h, w in zip(headers, widths)) + " |"
        sep_row = "|" + "|".join("-" * w for w in widths) + "|"

        rows = [header_row, sep_row]
        for result in self.results:
            rm = result.retrieval_metrics
            seg_f1 = result.segmentation_metrics.get("f1", 0.0)
            cells = [result.config.name]
            for k in resolved_k:
                cells.append(f"{rm.get(f'hit@{k}', 0.0):.4f}")
            cells.append(f"{rm.get('mrr', 0.0):.4f}")
            cells.append(f"{seg_f1:.4f}")
            rows.append("| " + " | ".join(c.ljust(w - 2) for c, w in zip(cells, widths)) + " |")

        return "\n".join(rows)

    def to_json(self, path: str | Path) -> None:
        dest = Path(path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        payload: dict[str, object] = {
            "generated_at": self.generated_at,
            "results": [r.to_dict() for r in self.results],
        }
        with dest.open("w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)

    def to_markdown(self, path: str | Path, k_values: list[int] | None = None) -> None:
        dest = Path(path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        header = f"# Evaluation Report\n\nGenerated: {self.generated_at}\n\n"
        with dest.open("w", encoding="utf-8") as fh:
            fh.write(header + self.to_table(k_values))

    def to_plots(self, output_dir: str | Path, k_values: list[int] | None = None) -> list[str]:
        if not _MPL_AVAILABLE:
            raise RuntimeError(_MPL_MISSING)

        resolved_k = k_values if k_values is not None else _DEFAULT_K_VALUES
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        saved: list[str] = []

        # grouped bar chart: Recall@K per config
        fig, ax = plt.subplots(figsize=(8, 5))
        n_configs = len(self.results)
        n_k = len(resolved_k)
        bar_width = 0.8 / max(n_configs, 1)
        x_positions = list(range(n_k))

        for cfg_idx, result in enumerate(self.results):
            rm = result.retrieval_metrics
            recalls = [rm.get(f"hit@{k}", 0.0) for k in resolved_k]
            offsets = [x + (cfg_idx - n_configs / 2 + 0.5) * bar_width for x in x_positions]
            ax.bar(offsets, recalls, width=bar_width, label=result.config.name)

        ax.set_xticks(x_positions)
        ax.set_xticklabels([f"K={k}" for k in resolved_k])
        ax.set_ylim(0.0, 1.0)
        ax.set_ylabel("Hit rate")
        ax.set_title("Hit@K Comparison Across Ablations")
        ax.yaxis.grid(True, linestyle="--", alpha=0.7)
        ax.set_axisbelow(True)
        ax.legend()
        plt.tight_layout()
        recall_path = out / "recall_comparison.png"
        fig.savefig(recall_path)
        plt.close(fig)
        saved.append(str(recall_path.resolve()))

        # horizontal bar chart: delta over baseline
        fig, ax = plt.subplots(figsize=(8, 5))

        metric_keys = [f"hit@{k}" for k in resolved_k] + ["mrr"]
        metric_labels = [f"Hit@{k}" for k in resolved_k] + ["MRR"]
        n_metrics = len(metric_keys)

        baseline = self.results[0].retrieval_metrics
        non_baseline = self.results[1:]
        n_non = len(non_baseline)

        bar_height = 0.8 / max(n_non, 1)
        y_positions = list(range(n_metrics))

        for cfg_idx, result in enumerate(non_baseline):
            rm = result.retrieval_metrics
            deltas = [rm.get(mk, 0.0) - baseline.get(mk, 0.0) for mk in metric_keys]
            offsets = [y + (cfg_idx - n_non / 2 + 0.5) * bar_height for y in y_positions]
            ax.barh(offsets, deltas, height=bar_height, label=result.config.name)

        ax.set_yticks(y_positions)
        ax.set_yticklabels(metric_labels)
        ax.axvline(x=0, color="black", linewidth=0.8)
        ax.set_xlabel("Delta from baseline")
        ax.set_title("Improvement Over Baseline")
        ax.legend()
        plt.tight_layout()
        delta_path = out / "delta_over_baseline.png"
        fig.savefig(delta_path)
        plt.close(fig)
        saved.append(str(delta_path.resolve()))

        return saved


def build_report(results: list[AblationResult]) -> EvalReport:
    from datetime import datetime, timezone

    return EvalReport(
        generated_at=datetime.now(timezone.utc).isoformat(),
        configs=[r.config for r in results],
        results=results,
    )
