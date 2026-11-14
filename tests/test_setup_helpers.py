from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile
import textwrap
import unittest


REPOSITORY = Path(__file__).resolve().parents[1]


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


class UpdateBrewSudoTests(unittest.TestCase):
    """Pin the sudo pre-authentication at the start of update-brew."""

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
        fake_bin = root / "bin"
        fake_bin.mkdir()
        self.calls = root / "calls"
        self.calls.touch()
        stubs = {
            "uname": 'printf "%s\\n" "$FAKE_UNAME"\n',
            "sudo": 'printf "sudo %s\\n" "$*" >> "$FAKE_CALLS"\nexit "$FAKE_SUDO_STATUS"\n',
            "brew": 'printf "brew %s\\n" "$*" >> "$FAKE_CALLS"\n',
        }
        for name, body in stubs.items():
            stub = fake_bin / name
            stub.write_text("#!/bin/sh\n" + body, encoding="utf-8")
            stub.chmod(0o755)
        self.environment = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith("GIT_") and key not in {"BASH_ENV", "ENV"}
        }
        self.environment.update(
            {
                "HOME": str(root),
                "PATH": f"{fake_bin}{os.pathsep}{self.environment['PATH']}",
                "FAKE_CALLS": str(self.calls),
            }
        )

    def run_recipe(self, uname: str, sudo_status: int) -> subprocess.CompletedProcess[str]:
        environment = dict(self.environment, FAKE_UNAME=uname, FAKE_SUDO_STATUS=str(sudo_status))
        return subprocess.run(
            [str(self.just), "--justfile", str(REPOSITORY / "Justfile"), "update-brew"],
            env=environment,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=60,
        )

    def calls_made(self) -> list[str]:
        return self.calls.read_text(encoding="utf-8").splitlines()

    def test_macos_without_sudo_stops_before_brew(self) -> None:
        completed = self.run_recipe("Darwin", 1)

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("sudo authentication failed", completed.stderr)
        self.assertEqual(self.calls_made(), ["sudo -v"])

    def test_macos_with_sudo_authenticates_before_brew_update(self) -> None:
        completed = self.run_recipe("Darwin", 0)

        self.assertEqual(completed.returncode, 0, completed.stderr)
        calls = self.calls_made()
        self.assertEqual(calls[:2], ["sudo -v", "brew update"])
        self.assertIn("brew upgrade", calls)

    def test_linux_skips_sudo(self) -> None:
        completed = self.run_recipe("Linux", 1)

        self.assertEqual(completed.returncode, 0, completed.stderr)
        calls = self.calls_made()
        self.assertEqual(calls[0], "brew update")
        self.assertNotIn("sudo -v", calls)


if __name__ == "__main__":
    unittest.main()
