#!/usr/bin/env python3
# python scripts/download_artifacts.py --finetune
# python scripts/download_artifacts.py --eval
# python scripts/download_artifacts.py --finetune --eval --force

from __future__ import annotations

import argparse
import logging
import sys
import zipfile
from pathlib import Path

log = logging.getLogger(__name__)

FINETUNE_GDRIVE_ID = (
    "https://drive.google.com/file/d/1KtIHGXUOXYk9_iRRW0WuJt8dMFPqU2OS/view?usp=sharing"
)
EVAL_GDRIVE_ID = (
    "https://drive.google.com/file/d/1PLtcTnIWsugFqkUPD0i_gruDD1B0kMAX/view?usp=sharing"
)

_FINETUNE_DATA_DIR = Path("runs/finetune/data")
_FINETUNE_SENTINEL = _FINETUNE_DATA_DIR / "train_hard.jsonl"
_EVAL_SENTINEL = Path("evaluation_output/sentences.json")


def _gdrive_download(url: str, dest: Path) -> None:
    try:
        import gdown
    except ImportError:
        log.error("gdown not installed -- run: pip install gdown --break-system-packages")
        sys.exit(1)

    gdown.download(url, str(dest), quiet=False, fuzzy=True)
    if not dest.exists():
        log.error("download produced no file at %s", dest)
        sys.exit(1)


def _download_finetune(force: bool) -> None:
    if _FINETUNE_SENTINEL.exists() and not force:
        log.info("finetune data already present, skipping (use --force to re-download)")
        return

    if FINETUNE_GDRIVE_ID == "FILL_IN":
        log.error("FINETUNE_GDRIVE_ID not set in download_artifacts.py")
        sys.exit(1)

    _FINETUNE_DATA_DIR.mkdir(parents=True, exist_ok=True)

    zip_path = _FINETUNE_DATA_DIR.parent / "finetune_artifacts.zip"
    print("Downloading finetune artifacts from Google Drive...")
    _gdrive_download(FINETUNE_GDRIVE_ID, zip_path)

    print("Extracting...")
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(_FINETUNE_DATA_DIR)
    zip_path.unlink()

    log.info("finetune artifacts ready at %s", _FINETUNE_DATA_DIR)


def _download_eval(force: bool) -> None:
    if _EVAL_SENTINEL.exists() and not force:
        log.info("eval data already present, skipping (use --force to re-download)")
        return

    if EVAL_GDRIVE_ID == "FILL_IN":
        log.error("EVAL_GDRIVE_ID not set in download_artifacts.py")
        sys.exit(1)

    # zip extracts relative to backend root, placing files at correct paths
    zip_path = Path("eval_artifacts.zip")
    print("Downloading evaluation artifacts from Google Drive...")
    _gdrive_download(EVAL_GDRIVE_ID, zip_path)

    print("Extracting...")
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(Path("."))
    zip_path.unlink()

    log.info("eval artifacts ready")


def main(argv=None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

    parser = argparse.ArgumentParser()
    parser.add_argument("--finetune", action="store_true")
    parser.add_argument("--eval", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)

    if not args.finetune and not args.eval:
        log.error("specify --finetune and/or --eval")
        sys.exit(1)

    if args.finetune:
        _download_finetune(args.force)
    if args.eval:
        _download_eval(args.force)


if __name__ == "__main__":
    main()
