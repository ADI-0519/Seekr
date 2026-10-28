#!/usr/bin/env python3
# python scripts/run_finetune_pipeline.py --output-dir runs/finetune/model_v4 --remote-train
# python scripts/run_finetune_pipeline.py --output-dir runs/finetune/model_v4 --no-use-prebuilt-data --video-ids 132,133,134

from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

log = logging.getLogger(__name__)

_PREBUILT_DATA_DIR = Path("runs/finetune/data")


def _run(cmd: list[str], label: str) -> None:
    log.info("running %s", label)
    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        log.error("%s failed (exit code %d)", label, result.returncode)
        sys.exit(result.returncode)


def _run_capture(cmd: list[str]) -> str | None:
    result = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def _count_jsonl_rows(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip())


def _load_json_if_exists(p: Path) -> dict | None:
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _assert_non_empty_split(triplets_dir: Path) -> None:
    split_path = triplets_dir / "split.json"
    split = _load_json_if_exists(split_path)
    if not split:
        log.error("missing or unreadable split metadata at %s", split_path)
        sys.exit(1)
    train_count = int(split.get("train_count", 0) or 0)
    check_count = int(split.get("check_count", 0) or 0)
    total_videos = int(split.get("total_videos", 0) or 0)
    if train_count == 0 or check_count == 0:
        log.error(
            "invalid split produced (train=%d, check=%d, videos=%d) -- "
            "need at least 2 distinct lectures in exported chunks",
            train_count,
            check_count,
            total_videos,
        )
        sys.exit(1)


def _wait_for_remote_training(model_dir: Path, label: str) -> None:
    task_id_file = model_dir / "clearml_task_id.txt"
    if not task_id_file.exists():
        log.error("clearml task id not found at %s", task_id_file)
        sys.exit(1)

    task_id = task_id_file.read_text(encoding="utf-8").strip()
    log.info("polling clearml task %s for %s", task_id, label)

    try:
        from clearml import Task as ClearMLTask
    except ImportError:
        log.error("clearml not installed, cannot poll remote task")
        sys.exit(1)

    remote_task: ClearMLTask = ClearMLTask.get_task(task_id=task_id)
    while True:
        status = remote_task.get_status()
        log.info("%s remote status: %s", label, status)
        if status == "completed":
            break
        if status in ("failed", "stopped", "closed"):
            log.error("remote %s failed with status: %s", label, status)
            sys.exit(1)
        time.sleep(30)

    # verify model artifact was produced, but don't download it locally (step fetches it from clearml via --finetune-task-id)
    model_artifact = remote_task.artifacts.get("model")
    if model_artifact is None:
        log.error("remote %s completed but no model artifact found", label)
        sys.exit(1)

    print(f"\nTraining complete. ClearML task ID: {task_id}")
    print("Pass this to run_evaluation.py with --finetune-task-id\n")


def _write_run_manifest(
    *,
    model_dir: Path,
    args: argparse.Namespace,
    started_at: datetime,
    finished_at: datetime,
    chunk_count: int,
    train_file: Path,
    check_file: Path,
) -> None:
    git_commit = _run_capture(["git", "rev-parse", "HEAD"])
    git_branch = _run_capture(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    git_dirty = bool(_run_capture(["git", "status", "--porcelain"]))

    manifest = {
        "started_at_utc": started_at.isoformat(),
        "finished_at_utc": finished_at.isoformat(),
        "duration_seconds": round((finished_at - started_at).total_seconds(), 3),
        "python_executable": sys.executable,
        "git": {"commit": git_commit, "branch": git_branch, "dirty": git_dirty},
        "pipeline_args": {
            "output_dir": str(args.output_dir),
            "use_prebuilt_data": args.use_prebuilt_data,
            "video_ids": getattr(args, "video_ids", None),
            "base_model": args.base_model,
            "epochs": args.epochs,
            "batch_size": args.batch_size,
            "grad_accum": args.grad_accum,
            "seed": args.seed,
            "hard_frac": args.hard_frac,
            "medium_frac": args.medium_frac,
            "mining_hard_frac": args.mining_hard_frac,
            "mining_medium_frac": args.mining_medium_frac,
            "clearml_task_name": args.clearml_task_name,
            "lr": args.lr,
            "warmup_ratio": args.warmup_ratio,
            "similarity_threshold": args.similarity_threshold,
            "remote_train": bool(args.remote_train),
        },
        "artifacts": {
            "train_jsonl": str(train_file),
            "check_jsonl": str(check_file),
            "model_dir": str(model_dir),
            "best_model_dir": str(model_dir / "best"),
            "final_model_dir": str(model_dir / "final"),
        },
        "counts": {
            "chunks": chunk_count,
            "train_triplets": _count_jsonl_rows(train_file),
            "check_triplets": _count_jsonl_rows(check_file),
        },
    }

    out_path = model_dir / "run_manifest.json"
    out_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    log.info("wrote run manifest to %s", out_path)


def main(argv=None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
    started_at = datetime.now(UTC)

    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("runs/finetune/model_v4"))
    # default is to use prebuilt data; pass --no-prebuilt-data to run full pipeline from DB
    parser.add_argument("--no-prebuilt-data", dest="use_prebuilt_data", action="store_false")
    parser.set_defaults(use_prebuilt_data=True)
    parser.add_argument("--video-ids", type=str, default=None)
    parser.add_argument("--base-model", type=str, default="BAAI/bge-m3")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--grad-accum", type=int, default=1)
    parser.add_argument("--lr", type=float, default=2e-5)
    parser.add_argument("--warmup-ratio", type=float, default=0.06)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--hard-frac", type=float, default=0.4)
    parser.add_argument("--medium-frac", type=float, default=0.3)
    parser.add_argument("--mining-hard-frac", type=float, default=0.4)
    parser.add_argument("--mining-medium-frac", type=float, default=0.3)
    parser.add_argument("--similarity-threshold", type=float, default=0.45)
    parser.add_argument("--clearml-task-name", type=str, default="finetune-bge-m3")
    parser.add_argument("--remote-train", action="store_true")
    # non-prebuilt path extra args
    parser.add_argument("--check-ratio", type=float, default=0.13)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--quality-strictness", choices=("low", "medium", "high"), default="medium")
    parser.add_argument("--force-export", action="store_true")
    args = parser.parse_args(argv)

    model_dir = args.output_dir
    model_dir.mkdir(parents=True, exist_ok=True)

    if args.use_prebuilt_data:
        data_dir = _PREBUILT_DATA_DIR
        chunks_file = data_dir / "chunks.jsonl"
        train_file = data_dir / "train_hard.jsonl"
        check_file = data_dir / "check.jsonl"

        if not train_file.exists():
            log.info("prebuilt data not found, downloading...")
            _run(
                [sys.executable, "scripts/download_artifacts.py", "--finetune"],
                "download finetune artifacts",
            )

        n_chunks = _count_jsonl_rows(chunks_file)
        log.info(
            "using prebuilt data: %d chunks, %d train, %d check triplets",
            n_chunks,
            _count_jsonl_rows(train_file),
            _count_jsonl_rows(check_file),
        )
    else:
        if not os.environ.get("DATABASE_URL"):
            log.error("DATABASE_URL not set -- required for non-prebuilt path")
            sys.exit(1)
        if not args.video_ids:
            log.error("--video-ids required when not using prebuilt data")
            sys.exit(1)

        data_dir = model_dir.parent / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        chunks_file = data_dir / "chunks.jsonl"
        triplets_dir = data_dir / "triplets"
        train_file = triplets_dir / "train.jsonl"
        check_file = triplets_dir / "check.jsonl"
        raw_triplets = data_dir / "raw_triplets.jsonl"

        if chunks_file.exists() and not args.force_export:
            n_chunks = _count_jsonl_rows(chunks_file)
            log.info("skipping export, using existing %s (%d chunks)", chunks_file, n_chunks)
        else:
            _run(
                [
                    sys.executable,
                    "-m",
                    "app.finetune.export",
                    "--output",
                    str(chunks_file),
                    "--video-ids",
                    args.video_ids,
                ],
                "export",
            )
            n_chunks = _count_jsonl_rows(chunks_file)

        if n_chunks == 0:
            log.error("no chunks exported, check DB connection and video IDs")
            sys.exit(1)

        synth_cmd = [
            sys.executable,
            "-m",
            "app.finetune.synth",
            "--chunks-file",
            str(chunks_file),
            "--output",
            str(raw_triplets),
            "--quality-strictness",
            args.quality_strictness,
        ]
        if args.limit is not None:
            synth_cmd += ["--limit", str(args.limit)]
        _run(synth_cmd, "synth")

        _run(
            [
                sys.executable,
                "-m",
                "app.finetune.build_triplets",
                "--chunks-file",
                str(chunks_file),
                "--raw-triplets",
                str(raw_triplets),
                "--output-dir",
                str(triplets_dir),
                "--check-ratio",
                str(args.check_ratio),
                "--seed",
                str(args.seed),
                "--similarity-threshold",
                str(args.similarity_threshold),
            ],
            "build_triplets",
        )
        _assert_non_empty_split(triplets_dir)

    train_cmd = [
        sys.executable,
        "-m",
        "app.finetune.train",
        "--train-data",
        str(train_file),
        "--check-data",
        str(check_file),
        "--output-dir",
        str(model_dir),
        "--base-model",
        args.base_model,
        "--chunks-file",
        str(chunks_file),
        "--structured",
        "--epochs",
        str(args.epochs),
        "--batch-size",
        str(args.batch_size),
        "--grad-accum",
        str(args.grad_accum),
        "--seed",
        str(args.seed),
        "--hard-frac",
        str(args.hard_frac),
        "--medium-frac",
        str(args.medium_frac),
        "--mining-hard-frac",
        str(args.mining_hard_frac),
        "--mining-medium-frac",
        str(args.mining_medium_frac),
        "--similarity-threshold",
        str(args.similarity_threshold),
        "--clearml-project",
        "Seekr",
        "--clearml-task-name",
        args.clearml_task_name,
        "--lr",
        str(args.lr),
        "--warmup-ratio",
        str(args.warmup_ratio),
        "--allow-model-download",
        *(["--remote"] if args.remote_train else []),
    ]
    _run(train_cmd, "train")

    if args.remote_train:
        _wait_for_remote_training(model_dir, "train")

    finished_at = datetime.now(UTC)
    _write_run_manifest(
        model_dir=model_dir,
        args=args,
        started_at=started_at,
        finished_at=finished_at,
        chunk_count=n_chunks,
        train_file=train_file,
        check_file=check_file,
    )

    log.info("pipeline completed, model saved to %s", model_dir)


if __name__ == "__main__":
    main()
