#!/usr/bin/env python3
# python scripts/run_evaluation.py --clearml-task-name evaluation-final --remote
# python scripts/run_evaluation.py --finetune-task-id <task_id> --remote

from __future__ import annotations

import argparse
import logging
import subprocess
import sys
from pathlib import Path

log = logging.getLogger(__name__)

_SENTENCES_JSON = Path("evaluation_output/sentences.json")
_GOLD_RETRIEVAL = Path("app/evaluation/fixtures/retrieval_gold.json")
_GOLD_SEGMENTATION = Path("app/evaluation/fixtures/segmentation_gold.json")


def _run(cmd: list[str], label: str) -> None:
    log.info("running %s", label)
    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        log.error("%s failed (exit code %d)", label, result.returncode)
        sys.exit(result.returncode)


def main(argv=None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

    parser = argparse.ArgumentParser()
    parser.add_argument("--finetune-task-id", type=str, default=None)
    parser.add_argument("--output-dir", type=Path, default=Path("evaluation_output/results"))
    parser.add_argument("--clearml-task-name", type=str, default="evaluation")
    parser.add_argument("--remote", action="store_true")
    parser.add_argument(
        "--sentences-json", type=Path, default=None, help="override default sentences.json path"
    )
    parser.add_argument(
        "--gold-retrieval", type=Path, default=None, help="override default retrieval gold path"
    )
    parser.add_argument(
        "--use-hyde",
        action="store_true",
        help="expand conceptual queries with HyDE before embedding",
    )
    args = parser.parse_args(argv)

    sentences_path = args.sentences_json or _SENTENCES_JSON
    gold_retrieval_path = args.gold_retrieval or _GOLD_RETRIEVAL

    missing_artifacts = (
        not sentences_path.exists()
        or not gold_retrieval_path.exists()
        or not _GOLD_SEGMENTATION.exists()
    )
    if missing_artifacts:
        log.info("eval artifacts missing, downloading...")
        _run(
            [sys.executable, "scripts/download_artifacts.py", "--eval"],
            "download eval artifacts",
        )

    missing = [
        p for p in (gold_retrieval_path, _GOLD_SEGMENTATION, sentences_path) if not p.exists()
    ]
    if missing:
        log.error("eval artifacts still missing after download: %s", [str(p) for p in missing])
        sys.exit(1)

    print()
    print("Running evaluation:")
    print(f"  sentences:    {sentences_path}")
    print(f"  retrieval:    {gold_retrieval_path}")
    print(f"  segmentation: {_GOLD_SEGMENTATION}")
    print(f"  output:       {args.output_dir}")
    print(f"  task name:    {args.clearml_task_name}")
    if args.finetune_task_id:
        print(f"  finetune ID:  {args.finetune_task_id}")
    if args.remote:
        print("  mode:         remote (ClearML agent)")
    print()

    cmd = [
        sys.executable,
        "-m",
        "app.evaluation.cli",
        "--sentences-json",
        str(sentences_path),
        "--gold-retrieval",
        str(gold_retrieval_path),
        "--gold-segmentation",
        str(_GOLD_SEGMENTATION),
        "--output-dir",
        str(args.output_dir),
        "--clearml-task-name",
        args.clearml_task_name,
    ]
    if args.finetune_task_id:
        cmd += ["--finetune-task-id", args.finetune_task_id]
    if args.remote:
        cmd.append("--remote")
    if args.use_hyde:
        cmd.append("--use-hyde")

    _run(cmd, "evaluation")
    log.info("evaluation complete, results at %s", args.output_dir)


if __name__ == "__main__":
    main()
