from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile
import textwrap
import unittest


REPOSITORY = Path(__file__).resolve().parents[1]


class SetupHelperTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        # Run the just binary that started the suite. Resolving `just` on PATH
        # under the fixture HOME can hit a version-manager shim that reads HOME.
        just = Path(os.environ.get("JUST", ""))
        if not just.is_absolute() or not os.access(just, os.X_OK):
            raise RuntimeError(
                "JUST must name the running just executable; run `just test-setup-helpers`"
            )
        cls.just = just

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.home = self.root / "home"
        self.fake_bin = self.root / "bin"
        self.library = self.root / "libsqlite3.so.0"
        self.target = self.home / ".local/lib/flutter-ffi/libsqlite3.so"
        self.home.mkdir()
        self.fake_bin.mkdir()
        self.library.write_bytes(b"sqlite fixture\n")
        ldconfig = self.fake_bin / "ldconfig"
        ldconfig.write_text(
            textwrap.dedent(
                f"""\
                #!/bin/sh
                printf '%s\\n' 'libsqlite3.so.0 (libc6) => {self.library}'
                """
            ),
            encoding="utf-8",
        )
        ldconfig.chmod(0o700)
        self.environment = {
            key: value
            for key, value in os.environ.items()
            if key not in {"BASH_ENV", "ENV", "ZDOTDIR"}
        }
        self.environment.update(
            {
                "HOME": str(self.home),
                "PATH": f"{self.fake_bin}{os.pathsep}{self.environment['PATH']}",
                "ZDOTDIR": str(self.root / "zdotdir"),
            }
        )

    def run_helper(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(self.just), "_link-libsqlite3"],
            cwd=REPOSITORY,
            env=self.environment,
            check=False,
            capture_output=True,
            text=True,
        )

    def test_exact_link_is_created_once_without_second_run_mutation(self) -> None:
        first = self.run_helper()
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertTrue(self.target.is_symlink())
        self.assertEqual(os.readlink(self.target), str(self.library))
        first_metadata = self.target.lstat()

        second = self.run_helper()
        self.assertEqual(second.returncode, 0, second.stderr)
        second_metadata = self.target.lstat()
        self.assertEqual(second_metadata.st_ino, first_metadata.st_ino)
        self.assertEqual(second_metadata.st_mtime_ns, first_metadata.st_mtime_ns)

    def test_foreign_symlink_is_refused_and_preserved(self) -> None:
        self.target.parent.mkdir(parents=True)
        foreign = self.root / "foreign"
        foreign.write_bytes(b"foreign fixture\n")
        self.target.symlink_to(foreign)

        completed = self.run_helper()

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("refusing to replace foreign symlink", completed.stderr)
        self.assertEqual(os.readlink(self.target), str(foreign))

    def test_regular_file_is_refused_and_preserved(self) -> None:
        self.target.parent.mkdir(parents=True)
        self.target.write_bytes(b"regular fixture\n")

        completed = self.run_helper()

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("refusing to replace non-symlink target", completed.stderr)
        self.assertEqual(self.target.read_bytes(), b"regular fixture\n")


TRACKED_ROBOREV_LINE = 'ROBOREV="/opt/homebrew/bin/roborev"'
LINUXBREW_ROBOREV_LINE = 'ROBOREV="/home/linuxbrew/.linuxbrew/bin/roborev"'


class RoborevInstallHookTests(unittest.TestCase):
    """Pin how setup keeps the tracked pre-push clean around roborev (#319)."""

    @classmethod
    def setUpClass(cls) -> None:
        just = Path(os.environ.get("JUST", ""))
        if not just.is_absolute() or not os.access(just, os.X_OK):
            raise RuntimeError(
                "JUST must name the running just executable; run `just test-setup-helpers`"
            )
        cls.just = just

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        root = Path(self.temporary.name)
        self.repo = root / "repo"
        self.fake_bin = root / "bin"
        self.calls = root / "roborev-calls"
        self.fake_bin.mkdir()
        self.environment = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith("GIT_") and key not in {"BASH_ENV", "ENV"}
        }
        self.environment.update(
            {
                "HOME": str(root),
                "PATH": f"{self.fake_bin}{os.pathsep}{self.environment['PATH']}",
                "FAKE_ROBOREV_CALLS": str(self.calls),
                "FAKE_ROBOREV_MODE": "none",
            }
        )

        # The fixture tracks the real pre-push so the test sees roborev's block
        # exactly as this repository ships it.
        hook = subprocess.run(
            ["git", "show", "HEAD:.githooks/pre-push"],
            cwd=REPOSITORY,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        self.assertIn(TRACKED_ROBOREV_LINE, hook.splitlines())
        self.hook = self.repo / ".githooks/pre-push"
        self.hook.parent.mkdir(parents=True)
        self.hook.write_text(hook, encoding="utf-8")
        self.hook.chmod(0o755)
        for arguments in (
            ["git", "init", "--quiet"],
            ["git", "add", ".githooks/pre-push"],
            [
                "git",
                "-c", "user.name=Fixture",
                "-c", "user.email=fixture@example.invalid",
                "-c", "commit.gpgsign=false",
                "commit", "--quiet", "-m", "fixture",
            ],
        ):
            subprocess.run(arguments, cwd=self.repo, env=self.environment, check=True)
        self.tracked = self.hook.read_text(encoding="utf-8")

        # Stand-in for `roborev install-hook`: "path" swaps the baked binary
        # line the way Linux installs do, "block" also bumps the block version.
        fake = self.fake_bin / "roborev"
        fake.write_text(
            textwrap.dedent(
                f"""\
                #!/usr/bin/env python3
                import os
                from pathlib import Path
                import sys

                with open(os.environ["FAKE_ROBOREV_CALLS"], "a", encoding="utf-8") as calls:
                    calls.write(os.getcwd() + " " + " ".join(sys.argv[1:]) + "\\n")
                mode = os.environ["FAKE_ROBOREV_MODE"]
                hook = Path(".githooks/pre-push")
                text = hook.read_text(encoding="utf-8")
                if mode in ("path", "block"):
                    text = text.replace({TRACKED_ROBOREV_LINE!r}, {LINUXBREW_ROBOREV_LINE!r})
                if mode == "block":
                    text = text.replace("pre-push hook v3", "pre-push hook v4")
                hook.write_text(text, encoding="utf-8")
                """
            ),
            encoding="utf-8",
        )
        fake.chmod(0o700)

    def run_helper(self, mode: str) -> subprocess.CompletedProcess[str]:
        environment = dict(self.environment, FAKE_ROBOREV_MODE=mode)
        return subprocess.run(
            [str(self.just), "_roborev-install-hook", str(self.repo)],
            cwd=REPOSITORY,
            env=environment,
            check=False,
            capture_output=True,
            text=True,
        )

    def status(self) -> str:
        return subprocess.run(
            ["git", "status", "--porcelain=v1"],
            cwd=self.repo,
            env=self.environment,
            check=True,
            capture_output=True,
            text=True,
        ).stdout

    def assert_installer_ran_once_in_repo(self) -> None:
        calls = self.calls.read_text(encoding="utf-8").splitlines()
        self.assertEqual(calls, [f"{self.repo.resolve()} install-hook"])

    def test_path_only_rewrite_is_restored(self) -> None:
        completed = self.run_helper("path")

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assert_installer_ran_once_in_repo()
        self.assertEqual(self.status(), "")
        self.assertEqual(self.hook.read_text(encoding="utf-8"), self.tracked)
        self.assertIn("Kept the tracked roborev path", completed.stdout)

    def test_unchanged_hook_stays_clean_and_quiet(self) -> None:
        completed = self.run_helper("none")

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assert_installer_ran_once_in_repo()
        self.assertEqual(self.status(), "")
        self.assertNotIn("Kept the tracked roborev path", completed.stdout)
        self.assertEqual(completed.stderr, "")

    def test_block_upgrade_is_left_for_review(self) -> None:
        completed = self.run_helper("block")

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("beyond its binary path", completed.stderr)
        hook = self.hook.read_text(encoding="utf-8")
        self.assertIn("pre-push hook v4", hook)
        self.assertIn(LINUXBREW_ROBOREV_LINE, hook.splitlines())

    def test_existing_local_edit_is_never_discarded(self) -> None:
        with self.hook.open("a", encoding="utf-8") as handle:
            handle.write("# local edit\n")

        completed = self.run_helper("path")

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("left as is", completed.stderr)
        lines = self.hook.read_text(encoding="utf-8").splitlines()
        self.assertEqual(lines[-1], "# local edit")
        self.assertIn(LINUXBREW_ROBOREV_LINE, lines)


if __name__ == "__main__":
    unittest.main()
