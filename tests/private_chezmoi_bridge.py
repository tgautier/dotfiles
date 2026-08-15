#!/usr/bin/env python3
"""Run private chezmoi checks without exposing companion output."""

from __future__ import annotations

import argparse
import hashlib
import hmac
import os
from pathlib import Path
import signal
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from typing import Protocol, Sequence


OWNERSHIP_TIMEOUT_SECONDS = 15
SOURCE_TIMEOUT_SECONDS = 60
CLEANUP_TIMEOUT_SECONDS = 2
CLEANUP_TERM_GRACE_SECONDS = 0.1
SNAPSHOT_TIMEOUT_SECONDS = 5
SNAPSHOT_CHUNK_BYTES = 1024 * 1024
PRIVATE_MODULES = {
    "ownership": "shared.chezmoi.check_target_ownership",
    "source": "shared.chezmoi.check_private_source",
}
PUBLIC_ONLY_STATE = "public-only"
COMPANION_STATE_PREFIX = "companion:"


class BridgeError(RuntimeError):
    """The optional companion checkout cannot satisfy its canary contract."""


class _Digest(Protocol):
    def update(self, value: bytes) -> None: ...


def _wait_without_reaping(process: subprocess.Popen[bytes], timeout: int | float) -> bool:
    deadline = time.monotonic() + timeout
    while True:
        result = os.waitid(
            os.P_PID,
            process.pid,
            os.WEXITED | os.WNOHANG | os.WNOWAIT,
        )
        if result is not None:
            return True
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return False
        time.sleep(min(0.01, remaining))


def _companion_path() -> Path:
    configured = os.environ.get("DOTFILES_PRIVATE_DIR")
    if configured:
        return Path(configured).expanduser()
    return Path.home() / "Workspace/tgautier/dotfiles-private"


def _resolved_companion() -> Path | None:
    checkout = _companion_path()
    if not checkout.exists() and not checkout.is_symlink():
        return None
    if not checkout.is_dir():
        raise BridgeError("companion checkout path is not a directory")
    try:
        return checkout.resolve(strict=True)
    except RuntimeError as exc:
        raise BridgeError("companion checkout path cannot be resolved") from exc


def _hash_field(digest: _Digest, value: bytes) -> None:
    digest.update(len(value).to_bytes(8, "big"))
    digest.update(value)


def _git_output(checkout: Path, arguments: Sequence[str], deadline: float) -> bytes:
    git = shutil.which("git")
    if git is None:
        raise BridgeError("companion repository state is unavailable")
    environment = {
        key: value for key, value in os.environ.items() if not key.startswith("GIT_")
    }
    environment["GIT_OPTIONAL_LOCKS"] = "0"
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise BridgeError("companion repository snapshot exceeded its deadline")
    try:
        completed = subprocess.run(
            [git, "-c", "core.fsmonitor=false", *arguments],
            cwd=checkout,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=remaining,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise BridgeError("companion repository state is unavailable") from exc
    if completed.returncode != 0:
        raise BridgeError("companion repository state is unavailable")
    return completed.stdout


def _snapshot_paths(checkout: Path, digest: _Digest, deadline: float) -> list[bytes]:
    git_marker = checkout / ".git"
    if git_marker.exists() or git_marker.is_symlink():
        _hash_field(
            digest,
            _git_output(
                checkout,
                ("rev-parse", "--verify", "HEAD^{commit}"),
                deadline,
            ),
        )
        _hash_field(
            digest,
            _git_output(
                checkout,
                (
                    "status",
                    "--porcelain=v2",
                    "-z",
                    "--untracked-files=all",
                    "--ignore-submodules=none",
                ),
                deadline,
            ),
        )
        serialized_paths = _git_output(
            checkout,
            ("ls-files", "-z", "--cached", "--others", "--exclude-standard"),
            deadline,
        )
        return sorted(
            path
            for path in set(serialized_paths.removesuffix(b"\0").split(b"\0"))
            if path
        )

    paths = []
    for path in checkout.rglob("*"):
        if time.monotonic() >= deadline:
            raise BridgeError("companion repository snapshot exceeded its deadline")
        if path.name != ".git":
            paths.append(os.fsencode(path.relative_to(checkout)))
    _hash_field(digest, b"non-git-companion")
    return sorted(paths)


def _hash_checkout_entry(
    checkout: Path,
    relative_bytes: bytes,
    digest: _Digest,
    deadline: float,
) -> None:
    if time.monotonic() >= deadline:
        raise BridgeError("companion repository snapshot exceeded its deadline")
    relative = Path(os.fsdecode(relative_bytes))
    if relative.is_absolute() or ".." in relative.parts:
        raise BridgeError("companion repository state is invalid")
    candidate = checkout / relative
    _hash_field(digest, relative_bytes)
    try:
        metadata = candidate.lstat()
    except FileNotFoundError:
        _hash_field(digest, b"missing")
        return
    _hash_field(digest, stat.S_IFMT(metadata.st_mode).to_bytes(8, "big"))
    _hash_field(digest, stat.S_IMODE(metadata.st_mode).to_bytes(8, "big"))
    if stat.S_ISLNK(metadata.st_mode):
        _hash_field(digest, os.fsencode(os.readlink(candidate)))
        return
    if stat.S_ISDIR(metadata.st_mode):
        return
    if not stat.S_ISREG(metadata.st_mode):
        raise BridgeError("companion repository contains an unsupported entry")

    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(candidate, flags)
    with os.fdopen(descriptor, "rb") as source:
        opened = os.fstat(source.fileno())
        if opened.st_dev != metadata.st_dev or opened.st_ino != metadata.st_ino:
            raise BridgeError("companion repository changed during snapshot")
        while chunk := source.read(SNAPSHOT_CHUNK_BYTES):
            digest.update(chunk)
            if time.monotonic() >= deadline:
                raise BridgeError("companion repository snapshot exceeded its deadline")
        finished = os.fstat(source.fileno())
    if (
        finished.st_size != opened.st_size
        or finished.st_mtime_ns != opened.st_mtime_ns
    ):
        raise BridgeError("companion repository changed during snapshot")


def _checkout_identity(checkout: Path) -> str:
    deadline = time.monotonic() + SNAPSHOT_TIMEOUT_SECONDS
    metadata = checkout.stat()
    digest = hashlib.sha256()
    for value in (
        os.fsencode(checkout),
        str(metadata.st_dev).encode("ascii"),
        str(metadata.st_ino).encode("ascii"),
    ):
        _hash_field(digest, value)
    for relative_bytes in _snapshot_paths(checkout, digest, deadline):
        _hash_checkout_entry(checkout, relative_bytes, digest, deadline)
    return digest.hexdigest()


def _publish_session_state(path: Path, state_value: str) -> None:
    if not path.is_absolute() or not path.parent.is_dir():
        raise BridgeError("companion canary state location is invalid")
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="ascii",
            dir=path.parent,
            prefix=f".{path.name}.",
            delete=False,
        ) as state_file:
            temporary = Path(state_file.name)
            state_file.write(f"{state_value}\n")
            state_file.flush()
            os.fsync(state_file.fileno())
        os.link(temporary, path, follow_symlinks=False)
    except FileExistsError as exc:
        raise BridgeError("companion canary state already exists") from exc
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _read_session_state(path: Path) -> str:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise BridgeError("companion canary state is unavailable") from exc
    with os.fdopen(descriptor, "rb") as state_file:
        metadata = os.fstat(state_file.fileno())
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_uid != os.getuid()
            or stat.S_IMODE(metadata.st_mode) & 0o077
        ):
            raise BridgeError("companion canary state is unsafe")
        serialized_state = state_file.read(129)
        if len(serialized_state) > 128 or not serialized_state.endswith(b"\n"):
            raise BridgeError("companion canary state is invalid")
    try:
        state_value = serialized_state[:-1].decode("ascii")
    except UnicodeDecodeError as exc:
        raise BridgeError("companion canary state is invalid") from exc
    if state_value == PUBLIC_ONLY_STATE:
        return state_value
    if state_value.startswith(COMPANION_STATE_PREFIX):
        identity = state_value.removeprefix(COMPANION_STATE_PREFIX)
        if len(identity) == 64 and all(character in "0123456789abcdef" for character in identity):
            return state_value
    raise BridgeError("companion canary state is invalid")


def _isolated_environment(root: Path) -> dict[str, str]:
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("GIT_", "PYTHON", "XDG_"))
        and key not in {"HOME", "VIRTUAL_ENV"}
    }
    isolated_paths = {
        "HOME": root / "operator-home",
        "XDG_CACHE_HOME": root / "operator-cache",
        "XDG_CONFIG_HOME": root / "operator-config",
        "XDG_DATA_HOME": root / "operator-data",
        "XDG_STATE_HOME": root / "operator-state",
    }
    for path in isolated_paths.values():
        path.mkdir(mode=0o700)
    environment.update({key: str(path) for key, path in isolated_paths.items()})
    return environment


def _stop_process_group(process: subprocess.Popen[bytes]) -> None:
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError):
        # waitid(..., WNOWAIT) keeps an exited leader unreaped, so ESRCH here
        # or macOS EPERM for a zombie-only group cannot expose a recycled PGID.
        process.wait(timeout=CLEANUP_TIMEOUT_SECONDS)
        return
    time.sleep(CLEANUP_TERM_GRACE_SECONDS)
    try:
        # The group leader remains unreaped until after this signal, pinning
        # the numeric process-group identity against PID reuse.
        os.killpg(process.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass
    try:
        process.wait(timeout=CLEANUP_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired as exc:
        raise BridgeError("companion process group exceeded its cleanup deadline") from exc


def _invoke_private(
    checkout: Path,
    module: str,
    arguments: Sequence[str],
    *,
    timeout: int | float,
) -> None:
    with tempfile.TemporaryDirectory(prefix="public-private-chezmoi-") as temporary:
        process = subprocess.Popen(
            [sys.executable, "-E", "-S", "-B", "-m", module, *arguments],
            cwd=checkout,
            env=_isolated_environment(Path(temporary)),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        completed = _wait_without_reaping(process, timeout)
        # A checker can exit after spawning a descendant. Keep its leader
        # unreaped until the complete group has received bounded cleanup.
        _stop_process_group(process)
        if not completed:
            raise BridgeError("companion check exceeded its bounded deadline")
        if process.returncode != 0:
            raise BridgeError(
                f"companion check failed with status {process.returncode}; output withheld"
            )


def run(mode: str, session_state: Path, public_targets: Path | None = None) -> str:
    expected_state = None
    if mode == "source":
        expected_state = _read_session_state(session_state)

    checkout = _resolved_companion()
    if checkout is None:
        if mode == "ownership":
            _publish_session_state(session_state, PUBLIC_ONLY_STATE)
            return "skipped"
        if expected_state == PUBLIC_ONLY_STATE:
            return "skipped"
        raise BridgeError("companion checkout changed during canary")
    identity = _checkout_identity(checkout)
    if mode == "source":
        if expected_state == PUBLIC_ONLY_STATE or not hmac.compare_digest(
            expected_state or "",
            f"{COMPANION_STATE_PREFIX}{identity}",
        ):
            raise BridgeError("companion checkout changed during canary")

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
    current_checkout = _resolved_companion()
    if (
        current_checkout is None
        or current_checkout != checkout
        or not hmac.compare_digest(_checkout_identity(current_checkout), identity)
    ):
        raise BridgeError("companion checkout changed during canary")
    if mode == "ownership":
        _publish_session_state(
            session_state,
            f"{COMPANION_STATE_PREFIX}{identity}",
        )
    return "passed"


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=tuple(PRIVATE_MODULES))
    parser.add_argument("--session-state", required=True, type=Path)
    parser.add_argument("--public-targets", type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    arguments = parse_args(argv)
    try:
        result = run(arguments.mode, arguments.session_state, arguments.public_targets)
    except BridgeError as exc:
        print(f"companion chezmoi: {exc}", file=sys.stderr)
        return 1
    except OSError:
        print(
            "companion chezmoi: companion check could not complete; details withheld",
            file=sys.stderr,
        )
        return 1
    print(f"companion chezmoi {arguments.mode}: {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
