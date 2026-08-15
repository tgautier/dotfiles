from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import signal
import stat
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from unittest import mock


BACKUP_DIGEST = "a" * 64
SCRIPT_PATH = Path(__file__).resolve().parents[1] / "bin/chezmoi-cutover"
LOADER = importlib.machinery.SourceFileLoader("chezmoi_cutover_tests", str(SCRIPT_PATH))
SPEC = importlib.util.spec_from_loader(LOADER.name, LOADER)
if SPEC is None:
    raise RuntimeError("could not load chezmoi operator module")
CUTOVER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = CUTOVER
LOADER.exec_module(CUTOVER)

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
        self.rcm_log = self.root / "rcm-invocations.jsonl"
        self.applied = self.root / "applied"
        self.backup = self.root / "rcm-links.json"
        self.canary_log = self.root / "canary.log"
        self.ready = self.root / "apply-ready"
        self.restore_ready = self.root / "restore-ready"
        self.descendant_pid = self.root / "descendant.pid"
        self.fake_chezmoi = self.root / "fake-chezmoi"
        self.home.mkdir()
        self._make_repository(self.public, private=False)
        self.script = self.public / "bin/chezmoi-cutover"
        self.fake_chezmoi.write_text(
            textwrap.dedent(
                """\
                #!/usr/bin/env python3
                import json
                import os
                from pathlib import Path
                import subprocess
                import sys
                import time

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
                            "DOTFILES_DIR",
                            "GIT_DIR",
                            "HOME",
                            "NO_COLOR",
                            "PYTHONPATH",
                            "RCM_LIB",
                            "RCRC",
                            "TERM",
                        )
                    },
                    "operation": operation,
                }
                with Path(os.environ["FAKE_CHEZMOI_LOG"]).open(
                    "a", encoding="utf-8"
                ) as handle:
                    handle.write(json.dumps(record, sort_keys=True) + "\\n")
                source = Path.cwd().name
                applied = Path(os.environ["FAKE_CHEZMOI_APPLIED"])
                marker = applied / source
                mutating_apply = operation == "apply" and "--dry-run" not in arguments
                if mutating_apply and os.environ.get(
                    "FAKE_CHEZMOI_FAIL_APPLY_CWD"
                ) == source:
                    raise SystemExit(29)
                if mutating_apply:
                    applied.mkdir(exist_ok=True)
                    marker.touch()
                    (Path(os.environ["HOME"]) / "unexpected-mutation").touch()
                    if os.environ.get("FAKE_CHEZMOI_WAIT_AFTER_APPLY_CWD") == source:
                        descendant = subprocess.Popen(
                            [
                                sys.executable,
                                "-c",
                                "import signal, time; "
                                "signal.signal(signal.SIGTERM, signal.SIG_IGN); "
                                "time.sleep(60)",
                            ]
                        )
                        Path(os.environ["FAKE_DESCENDANT_PID"]).write_text(
                            str(descendant.pid), encoding="utf-8"
                        )
                        Path(os.environ["FAKE_CHEZMOI_READY"]).touch()
                        while True:
                            time.sleep(1)
                elif not marker.exists():
                    print(f"fixture {source} {operation}")
                elif (
                    operation == "diff"
                    and os.environ.get("FAKE_CHEZMOI_POST_APPLY_DRIFT") == "1"
                ):
                    print(f"fixture {source} post-apply drift")
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
            (root / "rcrc").write_text("EXCLUDES=\"\"\n", encoding="utf-8")
            helper = root / "bin/rcm-links"
            helper.parent.mkdir()
            operator = root / "bin/chezmoi-cutover"
            operator.write_bytes(SCRIPT_PATH.read_bytes())
            operator.chmod(0o700)
            helper.write_text(
                textwrap.dedent(
                    """\
                    import json
                    import os
                    from pathlib import Path
                    import sys
                    import time

                    command = sys.argv[1]
                    with Path(os.environ["FAKE_RCM_LOG"]).open(
                        "a", encoding="utf-8"
                    ) as handle:
                        handle.write(json.dumps(sys.argv[1:]) + "\\n")
                    if command == "cutover-backup-verify":
                        print(
                            os.environ.get(
                                "FAKE_RCM_SUMMARY",
                                "cutover backup verified\\ttargets=1\\t"
                                f"approval_sha256={os.environ['FAKE_BACKUP_DIGEST']}",
                            )
                        )
                    elif command == "cutover-restore":
                        if os.environ.get("FAKE_RCM_RESTORE_FAIL") == "1":
                            raise SystemExit(31)
                        if os.environ.get("FAKE_RCM_RESTORE_DELAY") == "1":
                            Path(os.environ["FAKE_RCM_RESTORE_READY"]).touch()
                            time.sleep(1)
                        descendant_path = Path(os.environ["FAKE_DESCENDANT_PID"])
                        if descendant_path.exists():
                            try:
                                os.kill(int(descendant_path.read_text(encoding="utf-8")), 0)
                            except ProcessLookupError:
                                pass
                            else:
                                raise SystemExit(33)
                        print("cutover restore complete")
                    else:
                        raise SystemExit(32)
                    """
                ),
                encoding="utf-8",
            )
            canary = root / "tests/test-chezmoi-canary"
            canary.parent.mkdir()
            canary.write_text(
                textwrap.dedent(
                    """\
                    #!/usr/bin/env python3
                    import os
                    from pathlib import Path
                    import subprocess
                    import sys
                    import time

                    with Path(os.environ["FAKE_CANARY_LOG"]).open(
                        "a", encoding="utf-8"
                    ) as handle:
                        handle.write("passed\\n")
                    if os.environ.get("FAKE_CANARY_FAIL") == "1":
                        raise SystemExit(37)
                    if os.environ.get("FAKE_CANARY_WAIT") == "1":
                        descendant = subprocess.Popen(
                            [
                                sys.executable,
                                "-c",
                                "import signal, time; "
                                "signal.signal(signal.SIGTERM, signal.SIG_IGN); "
                                "time.sleep(60)",
                            ]
                        )
                        Path(os.environ["FAKE_DESCENDANT_PID"]).write_text(
                            str(descendant.pid), encoding="utf-8"
                        )
                        Path(os.environ["FAKE_CHEZMOI_READY"]).touch()
                        while True:
                            time.sleep(1)
                    """
                ),
                encoding="utf-8",
            )
            canary.chmod(0o700)
            bridge = root / "tests/private_chezmoi_bridge.py"
            bridge.write_text("# fixture bridge\n", encoding="utf-8")
            manifest = root / "docs/chezmoi-targets.tsv"
            manifest.parent.mkdir()
            manifest.write_text("fixture\n", encoding="utf-8")
            checker = root / "tests/check-chezmoi-targets"
            checker.write_text("# fixture checker\n", encoding="utf-8")
        if private:
            docs = root / "docs"
            docs.mkdir()
            (docs / "chezmoi-private-targets.tsv").write_text(
                "fixture\n", encoding="utf-8"
            )
            (docs / "chezmoi-dedicated-targets.tsv").write_text(
                "fixture\n", encoding="utf-8"
            )
            package = root / "shared/chezmoi"
            package.mkdir(parents=True)
            (package / "__init__.py").write_text("", encoding="utf-8")

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
                "FAKE_CHEZMOI_APPLIED": str(self.applied),
                "FAKE_RCM_LOG": str(self.rcm_log),
                "FAKE_RCM_RESTORE_READY": str(self.restore_ready),
                "FAKE_BACKUP_DIGEST": BACKUP_DIGEST,
                "FAKE_CANARY_LOG": str(self.canary_log),
                "FAKE_CHEZMOI_READY": str(self.ready),
                "FAKE_DESCENDANT_PID": str(self.descendant_pid),
                "CHEZMOI_CONFIG_FILE": str(self.root / "foreign-config"),
                "DOTFILES_DIR": str(self.root / "foreign-public"),
                "GIT_DIR": str(self.root / "foreign-git-dir"),
                "PYTHONPATH": str(self.root / "foreign-python"),
                "RCM_LIB": str(self.root / "foreign-rcm"),
                "RCRC": str(self.root / "foreign-rcrc"),
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

    def _approval(self, *, private: bool = True) -> str:
        completed = self._run(
            "plan",
            private=private,
            extra_arguments=[
                "--backup",
                str(self.backup),
                "--backup-confirm",
                BACKUP_DIGEST,
            ],
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        marker = "approval_sha256="
        self.assertIn(marker, completed.stdout)
        self.assertIn("fixture public status", completed.stdout)
        if private:
            self.assertIn("fixture private diff", completed.stdout)
        self.assertEqual(self.canary_log.read_text(encoding="utf-8"), "passed\n")
        return completed.stdout.rsplit(marker, maxsplit=1)[1].strip()

    def _rcm_records(self) -> list[list[str]]:
        if not self.rcm_log.exists():
            return []
        return [
            json.loads(line)
            for line in self.rcm_log.read_text(encoding="utf-8").splitlines()
        ]

    def _records(self) -> list[dict[str, object]]:
        if not self.log.exists():
            return []
        return [
            json.loads(line)
            for line in self.log.read_text(encoding="utf-8").splitlines()
        ]

    def _descendant_launcher(self, *, wait: bool) -> Path:
        launcher = self.root / f"descendant-launcher-{wait}"
        final_action = "time.sleep(60)" if wait else "raise SystemExit(0)"
        launcher.write_text(
            textwrap.dedent(
                f"""\
                #!/usr/bin/env python3
                import os
                from pathlib import Path
                import subprocess
                import sys
                import time

                child = subprocess.Popen(
                    [
                        sys.executable,
                        "-c",
                        "import signal, time; "
                        "signal.signal(signal.SIGTERM, signal.SIG_IGN); "
                        "time.sleep(60)",
                    ]
                )
                Path(os.environ["FAKE_DESCENDANT_PID"]).write_text(
                    str(child.pid), encoding="utf-8"
                )
                {final_action}
                """
            ),
            encoding="utf-8",
        )
        launcher.chmod(0o700)
        return launcher

    def _assert_process_gone(self, process_id: int) -> None:
        deadline = time.monotonic() + 1
        while True:
            try:
                os.kill(process_id, 0)
            except ProcessLookupError:
                return
            if time.monotonic() >= deadline:
                self.fail(f"descendant process {process_id} survived group cleanup")
            time.sleep(0.01)

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
        self.assertEqual(
            arguments[-4:],
            ["status", "--include", "files", "--path-style=relative"],
        )
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
        self.assertEqual(
            private_arguments[-4:],
            ["diff", "--include", "files", "--recursive"],
        )
        self.assertIn("==> private chezmoi diff", completed.stderr)

    def test_dry_run_never_invokes_mutating_apply(self) -> None:
        completed = self._run("dry-run", private=True)

        self.assertEqual(completed.returncode, 0, completed.stderr)
        records = self._records()
        self.assertEqual(len(records), 2)
        for record in records:
            arguments = record["arguments"]
            self.assertEqual(
                arguments[-5:],
                ["apply", "--include", "files", "--dry-run", "--verbose"],
            )
        self.assertFalse((self.home / "unexpected-mutation").exists())

    def test_environment_cannot_replace_config_home_or_git_context(self) -> None:
        completed = self._run("status")

        self.assertEqual(completed.returncode, 0, completed.stderr)
        environment = self._records()[0]["environment"]
        self.assertIsNone(environment["CHEZMOI_CONFIG_FILE"])
        self.assertIsNone(environment["DOTFILES_DIR"])
        self.assertIsNone(environment["GIT_DIR"])
        self.assertIsNone(environment["PYTHONPATH"])
        self.assertIsNone(environment["RCM_LIB"])
        self.assertIsNone(environment["RCRC"])
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
        self.assertIn("fixture private status", completed.stdout)

    def test_missing_chezmoi_executable_fails_before_invocation(self) -> None:
        completed = self._run(
            "status",
            extra_arguments=["--chezmoi", str(self.root / "missing-chezmoi")],
        )

        self.assertEqual(completed.returncode, 1)
        self.assertIn("chezmoi is not installed or is not executable", completed.stderr)
        self.assertEqual(self._records(), [])

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

    def test_empty_home_path_is_rejected_before_it_becomes_the_checkout(self) -> None:
        completed = self._run("status", extra_arguments=["--home", ""])

        self.assertEqual(completed.returncode, 2)
        self.assertIn("path must not be empty", completed.stderr)
        self.assertEqual(self._records(), [])

    def test_plan_reviews_both_sources_and_binds_the_backup(self) -> None:
        approval = self._approval()

        self.assertEqual(len(approval), 64)
        self.assertTrue(all(character in "0123456789abcdef" for character in approval))
        records = self._records()
        self.assertEqual(len(records), 6)
        self.assertEqual(
            [record["operation"] for record in records],
            ["status", "diff", "apply", "status", "diff", "apply"],
        )
        rcm_records = self._rcm_records()
        self.assertEqual(len(rcm_records), 1)
        self.assertEqual(rcm_records[0][0], "cutover-backup-verify")
        self.assertFalse(self.applied.exists())

    def test_approved_apply_runs_twice_and_finishes_settled(self) -> None:
        approval = self._approval()
        completed = self._run(
            "apply",
            private=True,
            extra_arguments=[
                "--backup",
                str(self.backup),
                "--backup-confirm",
                BACKUP_DIGEST,
                "--apply-confirm",
                approval,
            ],
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertTrue((self.applied / self.public.name).exists())
        self.assertTrue((self.applied / self.private.name).exists())
        self.assertIn("both sources are idempotent", completed.stderr)
        commands = [record[0] for record in self._rcm_records()]
        self.assertEqual(commands, [
            "cutover-backup-verify",
            "cutover-backup-verify",
            "cutover-backup-verify",
        ])

    def test_source_change_invalidates_approval_before_mutation(self) -> None:
        approval = self._approval()
        (self.public / "home/dot_fixture").write_text("changed\n", encoding="utf-8")

        completed = self._run(
            "apply",
            private=True,
            extra_arguments=[
                "--backup",
                str(self.backup),
                "--backup-confirm",
                BACKUP_DIGEST,
                "--apply-confirm",
                approval,
            ],
        )

        self.assertEqual(completed.returncode, 1)
        self.assertIn("apply approval differs", completed.stderr)
        self.assertFalse(self.applied.exists())
        self.assertNotIn("cutover-restore", [record[0] for record in self._rcm_records()])

    def test_recovery_contract_change_invalidates_approval_before_mutation(self) -> None:
        approval = self._approval()
        with (self.public / "rcrc").open("a", encoding="utf-8") as handle:
            handle.write("# changed after review\n")

        completed = self._run(
            "apply",
            private=True,
            extra_arguments=[
                "--backup",
                str(self.backup),
                "--backup-confirm",
                BACKUP_DIGEST,
                "--apply-confirm",
                approval,
            ],
        )

        self.assertEqual(completed.returncode, 1)
        self.assertIn("apply approval differs", completed.stderr)
        self.assertFalse(self.applied.exists())

    def test_operator_change_invalidates_approval_before_mutation(self) -> None:
        approval = self._approval()
        with self.script.open("a", encoding="utf-8") as handle:
            handle.write("\n# changed after review\n")

        completed = self._run(
            "apply",
            private=True,
            extra_arguments=[
                "--backup",
                str(self.backup),
                "--backup-confirm",
                BACKUP_DIGEST,
                "--apply-confirm",
                approval,
            ],
        )

        self.assertEqual(completed.returncode, 1)
        self.assertIn("apply approval differs", completed.stderr)
        self.assertFalse(self.applied.exists())

    def test_private_apply_failure_restores_the_complete_rcm_set(self) -> None:
        approval = self._approval()
        completed = self._run(
            "apply",
            private=True,
            extra_environment={"FAKE_CHEZMOI_FAIL_APPLY_CWD": self.private.name},
            extra_arguments=[
                "--backup",
                str(self.backup),
                "--backup-confirm",
                BACKUP_DIGEST,
                "--apply-confirm",
                approval,
            ],
        )

        self.assertEqual(completed.returncode, 1)
        self.assertIn("complete rcm link set was restored", completed.stderr)
        self.assertIn("cutover-restore", [record[0] for record in self._rcm_records()])

    def test_post_apply_drift_restores_rcm(self) -> None:
        approval = self._approval()
        completed = self._run(
            "apply",
            private=True,
            extra_environment={"FAKE_CHEZMOI_POST_APPLY_DRIFT": "1"},
            extra_arguments=[
                "--backup",
                str(self.backup),
                "--backup-confirm",
                BACKUP_DIGEST,
                "--apply-confirm",
                approval,
            ],
        )

        self.assertEqual(completed.returncode, 1)
        self.assertIn("first apply: public chezmoi diff is not empty", completed.stderr)
        self.assertIn("cutover-restore", [record[0] for record in self._rcm_records()])

    def test_recovery_failure_has_an_immediate_manual_boundary(self) -> None:
        approval = self._approval()
        completed = self._run(
            "apply",
            private=True,
            extra_environment={
                "FAKE_CHEZMOI_FAIL_APPLY_CWD": self.private.name,
                "FAKE_RCM_RESTORE_FAIL": "1",
            },
            extra_arguments=[
                "--backup",
                str(self.backup),
                "--backup-confirm",
                BACKUP_DIGEST,
                "--apply-confirm",
                approval,
            ],
        )

        self.assertEqual(completed.returncode, 1)
        self.assertIn("automatic rcm recovery also failed", completed.stderr)
        self.assertIn("run the documented recovery command immediately", completed.stderr)

    def test_backup_digest_mismatch_stops_before_review(self) -> None:
        completed = self._run(
            "plan",
            private=True,
            extra_environment={"FAKE_BACKUP_DIGEST": "b" * 64},
            extra_arguments=[
                "--backup",
                str(self.backup),
                "--backup-confirm",
                BACKUP_DIGEST,
            ],
        )

        self.assertEqual(completed.returncode, 1)
        self.assertIn("backup digest differs", completed.stderr)
        self.assertEqual(self._records(), [])

    def test_canary_failure_stops_before_review_and_apply(self) -> None:
        completed = self._run(
            "plan",
            private=True,
            extra_environment={"FAKE_CANARY_FAIL": "1"},
            extra_arguments=[
                "--backup",
                str(self.backup),
                "--backup-confirm",
                BACKUP_DIGEST,
            ],
        )

        self.assertEqual(completed.returncode, 1)
        self.assertIn("chezmoi canary failed with status 37", completed.stderr)
        self.assertEqual(self._records(), [])
        self.assertFalse(self.applied.exists())

    def test_sigterm_during_plan_stops_canary_descendant_without_restore(self) -> None:
        self._make_repository(self.private, private=True)
        environment = os.environ.copy()
        environment.update(
            {
                "FAKE_BACKUP_DIGEST": BACKUP_DIGEST,
                "FAKE_CANARY_LOG": str(self.canary_log),
                "FAKE_CANARY_WAIT": "1",
                "FAKE_CHEZMOI_APPLIED": str(self.applied),
                "FAKE_CHEZMOI_LOG": str(self.log),
                "FAKE_CHEZMOI_READY": str(self.ready),
                "FAKE_DESCENDANT_PID": str(self.descendant_pid),
                "FAKE_RCM_LOG": str(self.rcm_log),
            }
        )
        process = subprocess.Popen(
            [
                sys.executable,
                str(self.script),
                "plan",
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
                "--backup",
                str(self.backup),
                "--backup-confirm",
                BACKUP_DIGEST,
            ],
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.addCleanup(lambda: process.poll() is None and process.kill())
        for _ in range(200):
            if self.ready.exists():
                break
            if process.poll() is not None:
                self.fail("plan exited before reaching the canary signal fixture")
            time.sleep(0.05)
        else:
            self.fail("plan did not reach the canary signal fixture")

        process.send_signal(signal.SIGTERM)
        _stdout, stderr = process.communicate(timeout=10)

        self.assertEqual(process.returncode, 128 + signal.SIGTERM, stderr)
        self.assertIn("received SIGTERM", stderr)
        self.assertNotIn("restored", stderr)
        self.assertNotIn("cutover-restore", [record[0] for record in self._rcm_records()])
        descendant = int(self.descendant_pid.read_text(encoding="utf-8"))
        self._assert_process_gone(descendant)

    def test_chezmoi_timeout_is_reported_distinctly(self) -> None:
        source = CUTOVER.require_source(
            self.public,
            label="public",
            config=Path("chezmoi.toml"),
        )
        with (
            mock.patch.object(
                CUTOVER,
                "run_bounded_process",
                side_effect=CUTOVER.CutoverError("public chezmoi status exceeded 120 seconds"),
            ),
            self.assertRaisesRegex(CUTOVER.CutoverError, "exceeded 120 seconds"),
        ):
            CUTOVER.capture_operation(
                "status",
                executable=self.fake_chezmoi,
                source=source,
                home=self.home,
                cache_root=self.cache,
                state_root=self.state,
                show_output=False,
            )

    def test_process_timeout_kills_sigterm_ignoring_descendant(self) -> None:
        launcher = self._descendant_launcher(wait=True)
        environment = os.environ.copy()
        environment["FAKE_DESCENDANT_PID"] = str(self.descendant_pid)
        started = time.monotonic()

        with self.assertRaisesRegex(CUTOVER.CutoverError, "exceeded 1.0 seconds"):
            CUTOVER.run_bounded_process(
                [str(launcher)],
                cwd=self.root,
                environment=environment,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=1.0,
                label="descendant timeout fixture",
            )

        self.assertLess(time.monotonic() - started, 3)
        descendant = int(self.descendant_pid.read_text(encoding="utf-8"))
        self._assert_process_gone(descendant)

    def test_completed_process_cleans_remaining_descendant(self) -> None:
        launcher = self._descendant_launcher(wait=False)
        environment = os.environ.copy()
        environment["FAKE_DESCENDANT_PID"] = str(self.descendant_pid)

        returncode = CUTOVER.run_bounded_process(
            [str(launcher)],
            cwd=self.root,
            environment=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=2,
            label="completed descendant fixture",
        )

        self.assertEqual(returncode, 0)
        descendant = int(self.descendant_pid.read_text(encoding="utf-8"))
        self._assert_process_gone(descendant)

    def test_chezmoi_output_limit_is_enforced_before_reading_it(self) -> None:
        source = CUTOVER.require_source(
            self.public,
            label="public",
            config=Path("chezmoi.toml"),
        )

        def oversized_run(*arguments: object, **keywords: object) -> int:
            output = keywords["stdout"]
            output.write(b"x" * (CUTOVER.MAX_COMMAND_OUTPUT_BYTES + 1))
            return 0

        with (
            mock.patch.object(CUTOVER, "run_bounded_process", side_effect=oversized_run),
            self.assertRaisesRegex(CUTOVER.CutoverError, "output exceeds the safety limit"),
        ):
            CUTOVER.capture_operation(
                "status",
                executable=self.fake_chezmoi,
                source=source,
                home=self.home,
                cache_root=self.cache,
                state_root=self.state,
                show_output=False,
            )

    def test_rcm_helper_timeout_is_reported_distinctly(self) -> None:
        with (
            mock.patch.object(
                CUTOVER,
                "run_bounded_process",
                side_effect=CUTOVER.CutoverError("rcm cutover-backup-verify exceeded 90 seconds"),
            ),
            self.assertRaisesRegex(CUTOVER.CutoverError, "exceeded 90 seconds"),
        ):
            CUTOVER.run_rcm_helper(
                "cutover-backup-verify",
                public=self.public.resolve(),
                private=self.private,
                home=self.home,
                backup=self.backup,
                backup_confirm=None,
                lsrc="lsrc",
                rcup="rcup",
            )

    def test_rcm_helper_rejects_oversized_output_before_reading_it(self) -> None:
        def oversized_run(*arguments: object, **keywords: object) -> int:
            output = keywords["stdout"]
            output.write(b"x" * (CUTOVER.MAX_COMMAND_OUTPUT_BYTES + 1))
            return 0

        with (
            mock.patch.object(CUTOVER, "run_bounded_process", side_effect=oversized_run),
            self.assertRaisesRegex(CUTOVER.CutoverError, "output exceeds the safety limit"),
        ):
            CUTOVER.run_rcm_helper(
                "cutover-backup-verify",
                public=self.public.resolve(),
                private=self.private,
                home=self.home,
                backup=self.backup,
                backup_confirm=None,
                lsrc="lsrc",
                rcup="rcup",
            )

    def test_malformed_rcm_summary_stops_before_observation(self) -> None:
        completed = self._run(
            "plan",
            private=True,
            extra_environment={
                "FAKE_RCM_SUMMARY": (
                    "cutover backup verified\\ttargets=1\\t"
                    f"approval_sha256={BACKUP_DIGEST}\\tignored"
                )
            },
            extra_arguments=[
                "--backup",
                str(self.backup),
                "--backup-confirm",
                BACKUP_DIGEST,
            ],
        )

        self.assertEqual(completed.returncode, 1)
        self.assertIn("backup verification returned an invalid summary", completed.stderr)
        self.assertEqual(self._records(), [])

    def test_canary_timeout_stops_before_observation(self) -> None:
        self._make_repository(self.private, private=True)
        sources = CUTOVER.source_states(self.public, self.private)
        with (
            mock.patch.object(
                CUTOVER,
                "run_rcm_helper",
                return_value=(
                    "cutover backup verified\ttargets=1\t"
                    f"approval_sha256={BACKUP_DIGEST}"
                ),
            ),
            mock.patch.object(
                CUTOVER,
                "run_bounded_process",
                side_effect=CUTOVER.CutoverError("chezmoi canary exceeded 180 seconds"),
            ),
            self.assertRaisesRegex(CUTOVER.CutoverError, "exceeded 180 seconds"),
        ):
            CUTOVER.prepare_approval(
                executable=self.fake_chezmoi,
                sources=sources,
                public=self.public.resolve(),
                private=self.private.resolve(),
                home=self.home.resolve(),
                cache_root=self.cache,
                state_root=self.state,
                backup=self.backup,
                backup_confirm=BACKUP_DIGEST,
                lsrc="lsrc",
                rcup="rcup",
                show_output=False,
                canary=self.public / "tests/test-chezmoi-canary",
                run_canary_check=True,
            )

    def test_interrupted_first_apply_restores_rcm_before_failing(self) -> None:
        source = CUTOVER.require_source(
            self.public,
            label="public",
            config=Path("chezmoi.toml"),
        )
        with (
            mock.patch.object(CUTOVER, "prepare_approval", return_value=BACKUP_DIGEST),
            mock.patch.object(CUTOVER, "verify_backup"),
            mock.patch.object(CUTOVER, "capture_operation", side_effect=KeyboardInterrupt),
            mock.patch.object(CUTOVER, "restore_rcm") as restore,
            self.assertRaisesRegex(
                CUTOVER.CutoverError,
                "complete rcm link set was restored",
            ),
        ):
            CUTOVER.apply_with_recovery(
                executable=self.fake_chezmoi,
                sources=(source,),
                public=self.public.resolve(),
                private=self.private,
                home=self.home,
                cache_root=self.cache,
                state_root=self.state,
                backup=self.backup,
                backup_confirm=BACKUP_DIGEST,
                apply_confirm=BACKUP_DIGEST,
                lsrc="lsrc",
                rcup="rcup",
                canary=self.public / "tests/test-chezmoi-canary",
            )
        restore.assert_called_once()

    def test_apply_reruns_canary_and_refuses_mutation_when_it_fails(self) -> None:
        approval = self._approval()
        completed = self._run(
            "apply",
            private=True,
            extra_environment={"FAKE_CANARY_FAIL": "1"},
            extra_arguments=[
                "--backup",
                str(self.backup),
                "--backup-confirm",
                BACKUP_DIGEST,
                "--apply-confirm",
                approval,
            ],
        )

        self.assertEqual(completed.returncode, 1)
        self.assertIn("chezmoi canary failed with status 37", completed.stderr)
        self.assertFalse(self.applied.exists())
        self.assertNotIn("cutover-restore", [record[0] for record in self._rcm_records()])
        self.assertEqual(
            self.canary_log.read_text(encoding="utf-8").splitlines(),
            ["passed", "passed"],
        )

    def test_apply_preflight_withholds_failed_private_inspection_output(self) -> None:
        approval = self._approval()
        completed = self._run(
            "apply",
            private=True,
            extra_environment={"FAKE_CHEZMOI_FAIL_CWD": self.private.name},
            extra_arguments=[
                "--backup",
                str(self.backup),
                "--backup-confirm",
                BACKUP_DIGEST,
                "--apply-confirm",
                approval,
            ],
        )

        self.assertEqual(completed.returncode, 1)
        self.assertIn("private chezmoi status failed with status 23", completed.stderr)
        self.assertNotIn("fixture private status", completed.stdout)
        self.assertNotIn("fixture private status", completed.stderr)
        self.assertFalse(self.applied.exists())

    def test_sigterm_after_mutation_defers_exit_until_rcm_is_restored(self) -> None:
        approval = self._approval()
        if not self.private.exists():
            self._make_repository(self.private, private=True)
        environment = os.environ.copy()
        environment.update(
            {
                "FAKE_BACKUP_DIGEST": BACKUP_DIGEST,
                "FAKE_CANARY_LOG": str(self.canary_log),
                "FAKE_CHEZMOI_APPLIED": str(self.applied),
                "FAKE_CHEZMOI_LOG": str(self.log),
                "FAKE_CHEZMOI_READY": str(self.ready),
                "FAKE_DESCENDANT_PID": str(self.descendant_pid),
                "FAKE_CHEZMOI_WAIT_AFTER_APPLY_CWD": self.public.name,
                "FAKE_RCM_LOG": str(self.rcm_log),
            }
        )
        process = subprocess.Popen(
            [
                sys.executable,
                str(self.script),
                "apply",
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
                "--backup",
                str(self.backup),
                "--backup-confirm",
                BACKUP_DIGEST,
                "--apply-confirm",
                approval,
            ],
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.addCleanup(lambda: process.poll() is None and process.kill())
        for _ in range(200):
            if self.ready.exists():
                break
            if process.poll() is not None:
                self.fail("apply exited before reaching the mutation signal fixture")
            time.sleep(0.05)
        else:
            self.fail("apply did not reach the mutation signal fixture")

        process.send_signal(signal.SIGTERM)
        _stdout, stderr = process.communicate(timeout=10)

        self.assertEqual(process.returncode, 128 + signal.SIGTERM, stderr)
        self.assertIn("received SIGTERM", stderr)
        self.assertIn("complete rcm link set was restored", stderr)
        self.assertIn("cutover-restore", [record[0] for record in self._rcm_records()])
        descendant = int(self.descendant_pid.read_text(encoding="utf-8"))
        self._assert_process_gone(descendant)

    def test_sigterm_during_recovery_is_reported_after_restore(self) -> None:
        approval = self._approval()
        environment = os.environ.copy()
        environment.update(
            {
                "FAKE_BACKUP_DIGEST": BACKUP_DIGEST,
                "FAKE_CANARY_LOG": str(self.canary_log),
                "FAKE_CHEZMOI_APPLIED": str(self.applied),
                "FAKE_CHEZMOI_FAIL_APPLY_CWD": self.private.name,
                "FAKE_CHEZMOI_LOG": str(self.log),
                "FAKE_CHEZMOI_READY": str(self.ready),
                "FAKE_DESCENDANT_PID": str(self.descendant_pid),
                "FAKE_RCM_LOG": str(self.rcm_log),
                "FAKE_RCM_RESTORE_DELAY": "1",
                "FAKE_RCM_RESTORE_READY": str(self.restore_ready),
            }
        )
        process = subprocess.Popen(
            [
                sys.executable,
                str(self.script),
                "apply",
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
                "--backup",
                str(self.backup),
                "--backup-confirm",
                BACKUP_DIGEST,
                "--apply-confirm",
                approval,
            ],
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.addCleanup(lambda: process.poll() is None and process.kill())
        for _ in range(200):
            if self.restore_ready.exists():
                break
            if process.poll() is not None:
                self.fail("apply exited before reaching the recovery signal fixture")
            time.sleep(0.05)
        else:
            self.fail("apply did not reach the recovery signal fixture")

        process.send_signal(signal.SIGTERM)
        _stdout, stderr = process.communicate(timeout=10)

        self.assertEqual(process.returncode, 128 + signal.SIGTERM, stderr)
        self.assertIn("received SIGTERM", stderr)
        self.assertIn("complete rcm link set was restored", stderr)
        self.assertIn("cutover-restore", [record[0] for record in self._rcm_records()])

    def test_public_only_plan_uses_one_source(self) -> None:
        approval = self._approval(private=False)

        self.assertEqual(len(approval), 64)
        records = self._records()
        self.assertEqual(len(records), 3)
        self.assertEqual({record["cwd"] for record in records}, {str(self.public.resolve())})

    def test_shared_state_lock_rejects_a_concurrent_operator(self) -> None:
        state = CUTOVER.ensure_private_directory(self.state, label="fixture state")
        with CUTOVER.operator_lock(state):
            completed = self._run("status")

        self.assertEqual(completed.returncode, 1)
        self.assertIn("another chezmoi operator command is already running", completed.stderr)
        self.assertEqual(self._records(), [])


if __name__ == "__main__":
    unittest.main()
