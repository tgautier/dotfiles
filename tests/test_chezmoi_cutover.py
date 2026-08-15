from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import textwrap
import unittest


class ChezmoiCutoverTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.public = self.root / "public"
        self.private = self.root / "private"
        self.home = self.root / "home"
        self.cache = self.root / "cache"
        self.state = self.root / "state"
        self.log = self.root / "invocations.jsonl"
        self.script = Path(__file__).resolve().parents[1] / "bin/chezmoi-cutover"
        self.fake_chezmoi = self.root / "fake-chezmoi"
        self.home.mkdir()
        self._make_repository(self.public, private=False)
        self.fake_chezmoi.write_text(
            textwrap.dedent(
                """\
                #!/usr/bin/env python3
                import json
                import os
                from pathlib import Path
                import sys

                arguments = sys.argv[1:]
                operation = "apply" if "apply" in arguments else (
                    "diff" if "diff" in arguments else "status"
                )
                record = {
                    "arguments": arguments,
                    "cwd": str(Path.cwd()),
                    "environment": {
                        name: os.environ.get(name)
                        for name in (
                            "CHEZMOI_CONFIG_FILE",
                            "GIT_DIR",
                            "HOME",
                            "NO_COLOR",
                            "TERM",
                        )
                    },
                    "operation": operation,
                }
                with Path(os.environ["FAKE_CHEZMOI_LOG"]).open(
                    "a", encoding="utf-8"
                ) as handle:
                    handle.write(json.dumps(record, sort_keys=True) + "\\n")
                print(f"fixture {Path.cwd().name} {operation}")
                if operation == "apply" and "--dry-run" not in arguments:
                    (Path(os.environ["HOME"]) / "unexpected-mutation").touch()
                if os.environ.get("FAKE_CHEZMOI_FAIL_CWD") == Path.cwd().name:
                    raise SystemExit(23)
                """
            ),
            encoding="utf-8",
        )
        self.fake_chezmoi.chmod(0o700)

    def _make_repository(self, root: Path, *, private: bool) -> None:
        (root / "home").mkdir(parents=True)
        (root / ".chezmoiroot").write_text("home\n", encoding="utf-8")
        (root / "home/dot_fixture").write_text("fixture\n", encoding="utf-8")
        if private:
            (root / "chezmoi-private.toml").write_text(
                "umask = 63\n",
                encoding="utf-8",
            )
        else:
            (root / "chezmoi.toml").write_text(
                "umask = 18\n",
                encoding="utf-8",
            )

    def _run(
        self,
        operation: str,
        *,
        private: bool = False,
        extra_environment: dict[str, str] | None = None,
        extra_arguments: list[str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        if private and not self.private.exists():
            self._make_repository(self.private, private=True)
        environment = os.environ.copy()
        environment.update(
            {
                "FAKE_CHEZMOI_LOG": str(self.log),
                "CHEZMOI_CONFIG_FILE": str(self.root / "foreign-config"),
                "GIT_DIR": str(self.root / "foreign-git-dir"),
            }
        )
        if extra_environment:
            environment.update(extra_environment)
        arguments = [
            sys.executable,
            str(self.script),
            operation,
            "--home",
            str(self.home),
            "--public-dir",
            str(self.public),
            "--private-dir",
            str(self.private),
            "--cache-dir",
            str(self.cache),
            "--state-dir",
            str(self.state),
            "--chezmoi",
            str(self.fake_chezmoi),
        ]
        if extra_arguments:
            arguments.extend(extra_arguments)
        return subprocess.run(
            arguments,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            timeout=10,
        )

    def _records(self) -> list[dict[str, object]]:
        if not self.log.exists():
            return []
        return [
            json.loads(line)
            for line in self.log.read_text(encoding="utf-8").splitlines()
        ]

    def test_public_status_uses_explicit_isolated_state(self) -> None:
        completed = self._run("status")

        self.assertEqual(completed.returncode, 0, completed.stderr)
        records = self._records()
        self.assertEqual(len(records), 1)
        arguments = records[0]["arguments"]
        config_index = arguments.index("--config")
        self.assertEqual(
            arguments[config_index + 1],
            str((self.public / "chezmoi.toml").resolve()),
        )
        self.assertIn("--source", arguments)
        self.assertIn(str(self.public.resolve()), arguments)
        self.assertIn("--destination", arguments)
        self.assertIn(str(self.home.resolve()), arguments)
        self.assertIn(str(self.cache / "public"), arguments)
        self.assertIn(str(self.state / "public.boltdb"), arguments)
        self.assertEqual(arguments[-2:], ["status", "--path-style=relative"])
        self.assertIn("==> public chezmoi status", completed.stderr)
        self.assertIn("fixture public status", completed.stdout)
        self.assertFalse((self.home / "unexpected-mutation").exists())
        self.assertEqual(stat.S_IMODE(self.cache.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE(self.state.stat().st_mode), 0o700)

    def test_private_diff_runs_after_public_with_its_tracked_config(self) -> None:
        completed = self._run("diff", private=True)

        self.assertEqual(completed.returncode, 0, completed.stderr)
        records = self._records()
        self.assertEqual(
            [record["cwd"] for record in records],
            [str(self.public.resolve()), str(self.private.resolve())],
        )
        public_arguments = records[0]["arguments"]
        public_config_index = public_arguments.index("--config")
        self.assertEqual(
            public_arguments[public_config_index + 1],
            str((self.public / "chezmoi.toml").resolve()),
        )
        private_arguments = records[1]["arguments"]
        config_index = private_arguments.index("--config")
        self.assertEqual(
            private_arguments[config_index + 1],
            str((self.private / "chezmoi-private.toml").resolve()),
        )
        self.assertEqual(private_arguments[-2:], ["diff", "--recursive"])
        self.assertIn("==> private chezmoi diff", completed.stderr)

    def test_dry_run_never_invokes_mutating_apply(self) -> None:
        completed = self._run("dry-run", private=True)

        self.assertEqual(completed.returncode, 0, completed.stderr)
        records = self._records()
        self.assertEqual(len(records), 2)
        for record in records:
            arguments = record["arguments"]
            self.assertEqual(arguments[-3:], ["apply", "--dry-run", "--verbose"])
        self.assertFalse((self.home / "unexpected-mutation").exists())

    def test_environment_cannot_replace_config_home_or_git_context(self) -> None:
        completed = self._run("status")

        self.assertEqual(completed.returncode, 0, completed.stderr)
        environment = self._records()[0]["environment"]
        self.assertIsNone(environment["CHEZMOI_CONFIG_FILE"])
        self.assertIsNone(environment["GIT_DIR"])
        self.assertEqual(environment["HOME"], str(self.home.resolve()))
        self.assertEqual(environment["NO_COLOR"], "1")
        self.assertEqual(environment["TERM"], "dumb")

    def test_private_failure_stops_with_the_exact_source_label(self) -> None:
        completed = self._run(
            "status",
            private=True,
            extra_environment={"FAKE_CHEZMOI_FAIL_CWD": self.private.name},
        )

        self.assertEqual(completed.returncode, 1)
        self.assertEqual(len(self._records()), 2)
        self.assertIn("private chezmoi status failed with status 23", completed.stderr)

    def test_invalid_existing_private_path_fails_instead_of_skipping(self) -> None:
        self.private.write_text("not a checkout\n", encoding="utf-8")

        completed = self._run("status")

        self.assertEqual(completed.returncode, 1)
        self.assertEqual(self._records(), [])
        self.assertIn("private repository must be a non-symlink directory", completed.stderr)

    def test_symlinked_repository_is_rejected_before_execution(self) -> None:
        real_public = self.root / "real-public"
        self.public.rename(real_public)
        self.public.symlink_to(real_public, target_is_directory=True)

        completed = self._run("status")

        self.assertEqual(completed.returncode, 1)
        self.assertEqual(self._records(), [])
        self.assertIn("public repository must be a non-symlink directory", completed.stderr)

    def test_source_root_marker_must_be_exact(self) -> None:
        (self.public / ".chezmoiroot").write_text("other\n", encoding="utf-8")

        completed = self._run("status")

        self.assertEqual(completed.returncode, 1)
        self.assertEqual(self._records(), [])
        self.assertIn("must contain exactly 'home'", completed.stderr)

    def test_existing_runtime_directory_must_be_owner_only(self) -> None:
        self.state.mkdir(mode=0o755)
        self.state.chmod(0o755)

        completed = self._run("status")

        self.assertEqual(completed.returncode, 1)
        self.assertEqual(self._records(), [])
        self.assertIn("must not be accessible by group or other users", completed.stderr)

    def test_relative_runtime_override_is_rejected(self) -> None:
        completed = self._run(
            "status",
            extra_arguments=["--state-dir", "relative-state"],
        )

        self.assertEqual(completed.returncode, 1)
        self.assertEqual(self._records(), [])
        self.assertIn("state directory must be an absolute path", completed.stderr)


if __name__ == "__main__":
    unittest.main()
