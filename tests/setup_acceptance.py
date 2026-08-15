#!/usr/bin/env python3
"""Exercise the real setup/link path in a fresh checkout and isolated HOME."""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import textwrap
from typing import Iterable, Sequence


COMMAND_TIMEOUT_SECONDS = 600


class AcceptanceError(RuntimeError):
    """The fresh-checkout setup contract did not hold."""


@dataclass(frozen=True)
class TargetState:
    """Mutation-sensitive state for one managed HOME target."""

    kind: str
    mode: int
    inode: int
    modified_ns: int
    value: str


def run(
    arguments: Sequence[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    label: str,
) -> subprocess.CompletedProcess[str]:
    """Run one bounded command and withhold output on failure."""

    try:
        completed = subprocess.run(
            arguments,
            cwd=cwd,
            env=env,
            check=False,
            capture_output=True,
            text=True,
            timeout=COMMAND_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise AcceptanceError(f"{label} could not complete: {exc}") from exc
    if completed.returncode != 0:
        raise AcceptanceError(
            f"{label} failed with status {completed.returncode}; output withheld"
        )
    return completed


def require_clean_repository(root: Path, *, label: str) -> None:
    """Require a real, clean Git checkout at a committed tip."""

    root = root.resolve(strict=True)
    if not root.is_dir() or root == Path(root.anchor):
        raise AcceptanceError(f"{label} source must be a non-root directory")
    inside = run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        cwd=root,
        label=f"inspect {label} source",
    ).stdout.strip()
    if inside != "true":
        raise AcceptanceError(f"{label} source is not a Git worktree")
    status = run(
        ["git", "status", "--porcelain=v1"],
        cwd=root,
        label=f"inspect {label} source status",
    ).stdout
    if status:
        raise AcceptanceError(f"{label} source must be clean")


def fresh_checkout(source: Path, destination: Path, *, label: str) -> None:
    """Materialize tracked HEAD state and initialize an independent checkout."""

    archive = destination.parent / f"{destination.name}.tar"
    destination.mkdir(mode=0o700)
    run(
        ["git", "archive", "--format=tar", f"--output={archive}", "HEAD"],
        cwd=source,
        label=f"archive {label} source",
    )
    try:
        with tarfile.open(archive, mode="r:") as handle:
            destination_root = destination.resolve(strict=True)
            for member in handle.getmembers():
                candidate = (destination / member.name).resolve(strict=False)
                if candidate != destination_root and destination_root not in candidate.parents:
                    raise AcceptanceError(f"{label} archive contains an unsafe path")
            handle.extractall(destination, filter="data")
    except (OSError, tarfile.TarError) as exc:
        raise AcceptanceError(f"cannot extract {label} source: {exc}") from exc
    finally:
        archive.unlink(missing_ok=True)

    for arguments in (
        ["git", "init", "--quiet"],
        ["git", "config", "user.name", "Fresh Setup Acceptance"],
        ["git", "config", "user.email", "acceptance@example.invalid"],
        ["git", "add", "--all"],
        ["git", "-c", "commit.gpgsign=false", "commit", "--quiet", "-m", "fixture"],
    ):
        run(arguments, cwd=destination, label=f"initialize {label} checkout")


def write_fake_tools(fake_bin: Path, log_path: Path) -> None:
    """Install deterministic stand-ins for external provisioning only."""

    dispatcher = fake_bin / "acceptance-tool"
    dispatcher.write_text(
        textwrap.dedent(
            """\
            #!/usr/bin/env python3
            import json
            import os
            from pathlib import Path
            import sys

            command = Path(sys.argv[0]).name
            with Path(os.environ["SETUP_ACCEPTANCE_TOOL_LOG"]).open(
                "a", encoding="utf-8"
            ) as handle:
                handle.write(
                    json.dumps(
                        {"command": command, "arguments": sys.argv[1:]},
                        sort_keys=True,
                    )
                    + "\\n"
                )
            if command == "curl":
                print("unexpected network installer", file=sys.stderr)
                raise SystemExit(97)
            raise SystemExit(0)
            """
        ),
        encoding="utf-8",
    )
    dispatcher.chmod(0o755)
    for name in ("brew", "claude", "curl", "duti", "hermes", "mise", "roborev"):
        (fake_bin / name).symlink_to(dispatcher.name)
    log_path.touch(mode=0o600)


def clean_environment(home: Path, fake_bin: Path, log_path: Path) -> dict[str, str]:
    """Build an isolated process environment without inherited Git selectors."""

    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("GIT_")
        and key
        not in {
            "CDPATH",
            "CHEZMOI_CONFIG_FILE",
            "DOTFILES_DIR",
            "DOTFILES_PRIVATE_DIR",
            "ENV",
            "PYTHONHOME",
            "PYTHONPATH",
            "RCRC",
            "ZDOTDIR",
        }
    }
    environment.update(
        {
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "HOME": str(home),
            "LC_ALL": "C.UTF-8",
            "NO_COLOR": "1",
            "PATH": f"{fake_bin}{os.pathsep}{environment.get('PATH', '')}",
            "PYTHONDONTWRITEBYTECODE": "1",
            "SETUP_ACCEPTANCE_TOOL_LOG": str(log_path),
            "TERM": "dumb",
            "XDG_CACHE_HOME": str(home / ".cache"),
            "XDG_CONFIG_HOME": str(home / ".config"),
            "XDG_DATA_HOME": str(home / ".local/share"),
            "XDG_STATE_HOME": str(home / ".local/state"),
        }
    )
    return environment


def read_manifest(path: Path) -> list[dict[str, str]]:
    """Read a tab-separated ownership manifest."""

    try:
        with path.open(encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle, delimiter="\t"))
    except (OSError, csv.Error) as exc:
        raise AcceptanceError(f"cannot read ownership manifest {path.name}: {exc}") from exc


def sha256(path: Path) -> str:
    """Return a file digest without exposing its contents."""

    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise AcceptanceError(f"cannot hash managed target {path}: {exc}") from exc
    return digest.hexdigest()


def target_state(path: Path) -> TargetState:
    """Capture one target without following symlinks."""

    try:
        metadata = path.lstat()
    except OSError as exc:
        raise AcceptanceError(f"cannot inspect managed target {path}: {exc}") from exc
    mode = stat.S_IMODE(metadata.st_mode)
    if stat.S_ISLNK(metadata.st_mode):
        kind = "symlink"
        value = os.readlink(path)
    elif stat.S_ISREG(metadata.st_mode):
        kind = "file"
        value = sha256(path)
    else:
        raise AcceptanceError(f"managed target has unsupported shape: {path}")
    return TargetState(kind, mode, metadata.st_ino, metadata.st_mtime_ns, value)


def assert_regular_target(target: Path, source: Path, mode: int) -> None:
    """Require exact regular-file bytes and mode."""

    state = target_state(target)
    if state.kind != "file":
        raise AcceptanceError(f"expected a regular managed target: {target}")
    if state.mode != mode:
        raise AcceptanceError(
            f"managed target {target} has mode {state.mode:04o}, expected {mode:04o}"
        )
    if state.value != sha256(source):
        raise AcceptanceError(f"managed target bytes differ from source: {target}")


def assert_symlink_target(target: Path, source: Path) -> None:
    """Require an exact symlink to a repository source."""

    state = target_state(target)
    if state.kind != "symlink":
        raise AcceptanceError(f"expected a managed symlink: {target}")
    try:
        resolved = target.resolve(strict=True)
        expected = source.resolve(strict=True)
    except OSError as exc:
        raise AcceptanceError(f"cannot resolve managed symlink {target}: {exc}") from exc
    if resolved != expected:
        raise AcceptanceError(f"managed symlink points at the wrong source: {target}")


def verify_public_targets(public: Path, home: Path) -> set[Path]:
    """Verify every active public owner and return its HOME target set."""

    targets: set[Path] = set()
    for row in read_manifest(public / "docs/chezmoi-targets.tsv"):
        target = home / row["target"]
        disposition = row["disposition"]
        if disposition == "shadow":
            mode = 0o755 if row["mode"] == "executable" else 0o644
            assert_regular_target(target, public / "home" / row["chezmoi_source"], mode)
            targets.add(target)
        elif disposition.startswith("defer-"):
            assert_symlink_target(target, public / row["rcm_source"])
            targets.add(target)
        elif disposition in {"repository-only", "retire-at-cutover"}:
            continue
        else:
            raise AcceptanceError(f"unknown public disposition: {disposition}")
    return targets


def verify_private_targets(private: Path, home: Path, environment: dict[str, str]) -> set[Path]:
    """Verify private chezmoi and dedicated owners without printing their data."""

    for recipe in (
        "claude-directory-links-live-check",
        "claude-settings-check",
        "skills-live-check",
        "standing-rules-live-check",
        "agent-hooks-live-check",
    ):
        run(
            ["just", "-f", str(private / "Justfile"), recipe],
            cwd=private,
            env=environment,
            label=f"private {recipe}",
        )

    targets: set[Path] = set()
    for row in read_manifest(private / "docs/chezmoi-private-targets.tsv"):
        if row["disposition"] != "migrate":
            continue
        target = home / row["target"]
        assert_regular_target(
            target,
            private / "home" / row["chezmoi_source"],
            int(row["mode"], 8),
        )
        targets.add(target)

    for directory in (home / ".claude", home / ".ssh"):
        mode = stat.S_IMODE(directory.stat().st_mode)
        if mode != 0o700:
            raise AcceptanceError(
                f"private managed directory {directory} has mode {mode:04o}, expected 0700"
            )

    for row in read_manifest(private / "docs/chezmoi-dedicated-targets.tsv"):
        target = home / row["target"]
        state = target_state(target)
        expected_kind = "symlink" if row["target_shape"].endswith("symlink") else "file"
        if state.kind != expected_kind:
            raise AcceptanceError(f"dedicated target has the wrong shape: {target}")
        targets.add(target)
    return targets


def read_tool_log(log_path: Path) -> list[dict[str, object]]:
    """Read provisioning invocations from the deterministic fake tools."""

    try:
        return [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    except (OSError, json.JSONDecodeError) as exc:
        raise AcceptanceError(f"cannot read provisioning log: {exc}") from exc


def verify_provisioning_calls(log_path: Path, public: Path, *, runs: int) -> None:
    """Require the exact external provisioning boundary used by setup."""

    records = read_tool_log(log_path)
    by_command: dict[str, list[list[str]]] = {}
    for record in records:
        command = record.get("command")
        arguments = record.get("arguments")
        if not isinstance(command, str) or not isinstance(arguments, list):
            raise AcceptanceError("provisioning log contains an invalid record")
        by_command.setdefault(command, []).append(arguments)

    brewfile = public / ("Brewfile" if platform.system() == "Darwin" else "Brewfile.linux")
    expected_brew = ["bundle", "install", "--no-upgrade", f"--file={brewfile}"]
    if by_command.get("brew") != [expected_brew] * runs:
        raise AcceptanceError("setup did not invoke the expected Brewfile install")
    for command, expected in (("mise", ["install"]), ("roborev", ["install-hook"])):
        if by_command.get(command) != [expected] * runs:
            raise AcceptanceError(f"setup did not invoke the expected {command} command")
    if by_command.get("curl"):
        raise AcceptanceError("setup unexpectedly reached a network installer")
    if platform.system() == "Darwin" and not by_command.get("duti"):
        raise AcceptanceError("macOS setup did not configure editor associations")


def repository_is_clean(root: Path, *, label: str) -> None:
    """Require setup to leave fresh source contents unchanged."""

    status = run(
        ["git", "status", "--porcelain=v1"],
        cwd=root,
        label=f"inspect {label} checkout after setup",
    ).stdout
    if status:
        raise AcceptanceError(f"setup modified the fresh {label} checkout")


def case_label(profile_name: str | None, companion: bool) -> str:
    """Return a non-sensitive acceptance case label."""

    system = platform.system()
    if system == "Linux":
        release = platform.release().lower()
        platform_name = "wsl2" if "microsoft" in release else "linux"
    elif system == "Darwin":
        platform_name = "macos"
    else:
        platform_name = system.lower()
    profile_part = f"/{profile_name}" if profile_name else ""
    companion_part = "with-companion" if companion else "public-only"
    return f"{platform_name}{profile_part}/{companion_part}"


def run_case(
    public_source: Path,
    private_source: Path | None,
    *,
    profile_name: str | None,
) -> None:
    """Run setup twice in one fresh checkout and prove exact idempotence."""

    with tempfile.TemporaryDirectory(prefix="dotfiles-setup-acceptance-") as raw_root:
        root = Path(raw_root).resolve(strict=True)
        public = root / "public"
        private = root / "private" if private_source else None
        home = root / "home"
        fake_bin = root / "fake-bin"
        tool_log = root / "tool-invocations.jsonl"
        home.mkdir(mode=0o700)
        fake_bin.mkdir(mode=0o700)
        fresh_checkout(public_source, public, label="public")
        if private_source and private:
            fresh_checkout(private_source, private, label="private")
        write_fake_tools(fake_bin, tool_log)
        environment = clean_environment(home, fake_bin, tool_log)
        environment["DOTFILES_DIR"] = str(public)
        environment["DOTFILES_PRIVATE_DIR"] = str(private or root / "absent-private")

        if platform.system() == "Darwin":
            if profile_name not in {"work", "personal"}:
                raise AcceptanceError("macOS acceptance requires a work or personal profile")
            marker = home / ".config/dotfiles/profile"
            marker.parent.mkdir(parents=True)
            marker.write_text(f"{profile_name}\n", encoding="utf-8")
        elif profile_name is not None:
            raise AcceptanceError("machine profiles are macOS-only")

        managed_targets: set[Path] = set()
        first_state: dict[Path, TargetState] | None = None
        for invocation in (1, 2):
            run(
                ["just", "setup"],
                cwd=public,
                env=environment,
                label=f"setup pass {invocation}",
            )
            managed_targets = verify_public_targets(public, home)
            if private:
                managed_targets.update(verify_private_targets(private, home, environment))
            if platform.system() == "Darwin":
                managed_targets.add(home / ".config/dotfiles/profile")
            else:
                managed_targets.add(home / ".local/lib/flutter-ffi/libsqlite3.so")

            current_state = {target: target_state(target) for target in managed_targets}
            if first_state is None:
                first_state = current_state
            elif current_state != first_state:
                raise AcceptanceError("the second setup pass mutated managed target state")

        verify_provisioning_calls(tool_log, public, runs=2)
        hooks_path = run(
            ["git", "config", "--local", "--get", "core.hooksPath"],
            cwd=public,
            label="inspect fresh checkout Git hooks",
        ).stdout.strip()
        if hooks_path != ".githooks":
            raise AcceptanceError("setup did not wire the fresh checkout Git hooks")
        repository_is_clean(public, label="public")
        if private:
            repository_is_clean(private, label="private")

    print(f"fresh setup acceptance passed: {case_label(profile_name, private is not None)}")


def profiles() -> Iterable[str | None]:
    """Return every profile supported by the current platform."""

    if platform.system() == "Darwin":
        return ("work", "personal")
    if platform.system() == "Linux":
        return (None,)
    raise AcceptanceError(f"unsupported acceptance platform: {platform.system()}")


def parse_arguments() -> argparse.Namespace:
    """Parse the repository and optional companion inputs."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--public-source",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="clean public checkout to archive (default: this repository)",
    )
    parser.add_argument(
        "--private-source",
        type=Path,
        help="clean private companion checkout; adds companion-present cases",
    )
    return parser.parse_args()


def main() -> int:
    """Run the platform's public-only and optional companion acceptance matrix."""

    arguments = parse_arguments()
    try:
        public_source = arguments.public_source.resolve(strict=True)
        require_clean_repository(public_source, label="public")
        private_source = None
        if arguments.private_source is not None:
            private_source = arguments.private_source.resolve(strict=True)
            require_clean_repository(private_source, label="private")
        for profile_name in profiles():
            run_case(public_source, None, profile_name=profile_name)
            if private_source:
                run_case(public_source, private_source, profile_name=profile_name)
    except (AcceptanceError, OSError) as exc:
        print(f"fresh setup acceptance failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
