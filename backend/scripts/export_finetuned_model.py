#!/usr/bin/env python3
# python scripts/export_finetuned_model.py --task-id <clearml_task_id>

# downloads fine-tuned BGE-M3 checkpoint from ClearML training task to the host
from __future__ import annotations

import argparse
import logging
import re
import shutil
import sys
from pathlib import Path

log = logging.getLogger(__name__)

# Compose mounts runs/finetune at /models/finetuned and the application reads
# /models/finetuned/best, so the exported artifact must land directly here.
_DEFAULT_OUTPUT = Path("runs/finetune")
_ENV_PATH = Path("../.env")
_CONTAINER_MODEL_PATH = "/models/finetuned/best"


def _update_env(env_path: Path) -> None:
    line = f"EMBEDDING_MODEL={_CONTAINER_MODEL_PATH}"
    if not env_path.exists():
        log.warning(".env not found at %s, skipping env update", env_path)
        return
    content = env_path.read_text(encoding="utf-8")
    if re.search(r"^EMBEDDING_MODEL=", content, re.MULTILINE):
        content = re.sub(r"^EMBEDDING_MODEL=.*", line, content, flags=re.MULTILINE)
    else:
        content = content.rstrip("\n") + "\n" + line + "\n"
    env_path.write_text(content, encoding="utf-8")
    log.info("set %s in %s", line, env_path)


def main(argv=None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

    parser = argparse.ArgumentParser()
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--output-dir", type=Path, default=_DEFAULT_OUTPUT)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)

    best_dir = args.output_dir / "best"
    if best_dir.exists() and not args.force:
        log.info("model already present at %s, skipping (use --force to re-download)", best_dir)
        _update_env(_ENV_PATH)
        return

    try:
        from clearml import Task as ClearMLTask
    except ImportError:
        log.error("clearml not installed -- run: pip install clearml")
        sys.exit(1)

    log.info("fetching model artifact from clearml task %s", args.task_id)
    task: ClearMLTask = ClearMLTask.get_task(task_id=args.task_id)

    artifact = task.artifacts.get("model")
    if artifact is None:
        log.error("no model artifact found on task %s", args.task_id)
        sys.exit(1)

    log.info("downloading model artifact (this may take a while)...")
    local_copy = Path(artifact.get_local_copy())

    args.output_dir.mkdir(parents=True, exist_ok=True)
    shutil.copytree(str(local_copy), str(args.output_dir), dirs_exist_ok=True)
    log.info("model saved to %s", args.output_dir)

    _update_env(_ENV_PATH)
    print("\nFine-tuned model ready. Restart the stack to activate: docker compose up -d\n")


if __name__ == "__main__":
    main()
