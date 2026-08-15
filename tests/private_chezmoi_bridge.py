#!/usr/bin/env python3
"""Run private chezmoi checks without exposing companion output."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import signal
import subprocess
import sys
from typing import Sequence


OWNERSHIP_TIMEOUT_SECONDS = 15
SOURCE_TIMEOUT_SECONDS = 60
CLEANUP_TIMEOUT_SECONDS = 2
PRIVATE_MODULES = {
    "ownership": "shared.chezmoi.check_target_ownership",
    "source": "shared.chezmoi.check_private_source",
}


class BridgeError(RuntimeError):
    """The optional companion checkout cannot satisfy its canary contract."""


def _companion_path() -> Path:
    configured = os.environ.get("DOTFILES_PRIVATE_DIR")
    if configured:
        return Path(configured).expanduser()
    return Path.home() / "Workspace/tgautier/dotfiles-private"


def _isolated_environment() -> dict[str, str]:
    return {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("GIT_", "PYTHON")) and key != "VIRTUAL_ENV"
    }


def _stop_process_group(process: subprocess.Popen[bytes]) -> None:
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        process.communicate()
        return
    try:
        process.communicate(timeout=CLEANUP_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        pass
    try:
        # The direct child may have exited on SIGTERM while one of its own
        # children ignored the group signal. Always address the group again;
        # ProcessLookupError is the positive signal that no member remains.
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    if process.poll() is None:
        process.communicate()


def _invoke_private(
    checkout: Path,
    module: str,
    arguments: Sequence[str],
    *,
    timeout: int | float,
) -> None:
    process = subprocess.Popen(
        [sys.executable, "-E", "-S", "-B", "-m", module, *arguments],
        cwd=checkout,
        env=_isolated_environment(),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    try:
        process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        _stop_process_group(process)
        raise BridgeError("companion check exceeded its bounded deadline") from exc
    if process.returncode != 0:
        raise BridgeError(
            f"companion check failed with status {process.returncode}; output withheld"
        )


def run(mode: str, public_targets: Path | None = None) -> str:
    checkout = _companion_path()
    if not checkout.exists() and not checkout.is_symlink():
        return "skipped"
    if not checkout.is_dir():
        raise BridgeError("companion checkout path is not a directory")
    checkout = checkout.resolve(strict=True)

    module = PRIVATE_MODULES[mode]
    module_path = checkout.joinpath(*module.split(".")).with_suffix(".py")
    if not module_path.is_file():
        raise BridgeError("companion checkout is incompatible; update it before retrying")

    arguments: list[str] = []
    timeout = SOURCE_TIMEOUT_SECONDS
    if mode == "ownership":
        if public_targets is None or not public_targets.is_file():
            raise BridgeError("public target manifest is unavailable")
        arguments = ["--public-targets", str(public_targets.resolve(strict=True))]
        timeout = OWNERSHIP_TIMEOUT_SECONDS

    _invoke_private(checkout, module, arguments, timeout=timeout)
    return "passed"


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=tuple(PRIVATE_MODULES))
    parser.add_argument("--public-targets", type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    arguments = parse_args(argv)
    try:
        result = run(arguments.mode, arguments.public_targets)
    except (BridgeError, OSError) as exc:
        print(f"companion chezmoi: {exc}", file=sys.stderr)
        return 1
    print(f"companion chezmoi {arguments.mode}: {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
