from __future__ import annotations

import subprocess
from unittest.mock import call, patch

import pytest

from scripts import start


def test_cpu_uses_only_base_compose_file() -> None:
    assert start.compose_command("cpu") == [
        "docker",
        "compose",
        "-f",
        "docker-compose.yml",
    ]


def test_gpu_adds_the_gpu_override() -> None:
    assert start.compose_command("gpu") == [
        "docker",
        "compose",
        "-f",
        "docker-compose.yml",
        "-f",
        "docker-compose.gpu.yml",
    ]


@patch("scripts.start.run")
def test_normal_start_does_not_rebuild_or_initialize_models(run_mock) -> None:
    start.main(["cpu"])

    compose = start.compose_command("cpu")
    assert run_mock.call_args_list == [
        call([*compose, "config", "--quiet"]),
        call([*compose, "up", "--detach"]),
    ]


@patch("scripts.start.time.sleep")
@patch("scripts.start.run")
def test_model_initialization_retries(run_mock, sleep_mock) -> None:
    run_mock.side_effect = [None, subprocess.CalledProcessError(1, "docker"), None]

    start.initialize_models(start.compose_command("cpu"))

    assert run_mock.call_count == 3
    sleep_mock.assert_called_once_with(10)


def test_unknown_mode_is_rejected() -> None:
    with pytest.raises(SystemExit, match="2"):
        start.parse_args(["not-a-mode"])
