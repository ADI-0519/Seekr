#!/usr/bin/env python3
"""Start the local backend stack in CPU or GPU mode."""

from __future__ import annotations

import argparse
import subprocess
import time
from pathlib import Path
from typing import Sequence

BACKEND_DIR = Path(__file__).resolve().parents[1]
MODEL_INIT_ATTEMPTS = 5


def compose_command(mode: str) -> list[str]:
    """Return the Docker Compose command for the requested worker mode."""
    command = ["docker", "compose", "-f", "docker-compose.yml"]
    if mode == "gpu":
        command.extend(["-f", "docker-compose.gpu.yml"])
    return command


def run(command: Sequence[str]) -> None:
    """Run a command from the backend directory and fail on errors."""
    subprocess.run(command, cwd=BACKEND_DIR, check=True)


def initialize_models(compose: Sequence[str]) -> None:
    """Build and run the optional model-cache initializer with bounded retries."""
    setup = [*compose, "--profile", "setup"]
    run([*setup, "build", "model-init"])

    for attempt in range(1, MODEL_INIT_ATTEMPTS + 1):
        try:
            run([*setup, "run", "--rm", "model-init"])
            return
        except subprocess.CalledProcessError:
            if attempt == MODEL_INIT_ATTEMPTS:
                raise
            print(
                f"Model initialization failed (attempt {attempt}/"
                f"{MODEL_INIT_ATTEMPTS}); retrying in 10 seconds..."
            )
            time.sleep(10)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "mode",
        choices=("cpu", "gpu"),
        nargs="?",
        default="cpu",
        help="worker runtime; defaults to cpu",
    )
    parser.add_argument(
        "--build",
        action="store_true",
        help="rebuild application images before starting",
    )
    parser.add_argument(
        "--setup-models",
        action="store_true",
        help="download and cache ML models before starting",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    compose = compose_command(args.mode)

    run([*compose, "config", "--quiet"])
    if args.setup_models:
        initialize_models(compose)

    up = [*compose, "up", "--detach"]
    if args.build:
        up.append("--build")
    run(up)


if __name__ == "__main__":
    main()
