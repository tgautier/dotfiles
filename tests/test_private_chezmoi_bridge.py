from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import io
import os
from pathlib import Path
import tempfile
import textwrap
import time
import unittest
from unittest import mock

import private_chezmoi_bridge as bridge


PRIVATE_SENTINEL = "private fixture value"


class PrivateChezmoiBridgeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.checkout = self.root / "companion"
        self.manifest = self.root / "public-targets.tsv"
        self.session_state = self.root / "companion-session"
        self.manifest.write_text("fixture\n", encoding="utf-8")

    def _module(self, name: str, body: str) -> None:
        module = self.checkout / "shared/chezmoi" / f"{name}.py"
        module.parent.mkdir(parents=True, exist_ok=True)
        (module.parent / "__init__.py").touch()
        module.write_text(textwrap.dedent(body), encoding="utf-8")

    def _environment(self):
        return mock.patch.dict(
            os.environ,
            {"DOTFILES_PRIVATE_DIR": str(self.checkout)},
            clear=False,
        )

    def _main_arguments(self, mode: str) -> list[str]:
        arguments = [mode, "--session-state", str(self.session_state)]
        if mode == "ownership":
            arguments.extend(("--public-targets", str(self.manifest)))
        return arguments

    def _authorize_source(self) -> None:
        self._module("check_target_ownership", "")
        with self._environment():
            result = bridge.run("ownership", self.session_state, self.manifest)
        self.assertEqual(result, "passed")

    def test_absent_checkout_skips_without_printing_its_path(self) -> None:
        output = io.StringIO()
        with self._environment(), redirect_stdout(output):
            result = bridge.main(self._main_arguments("ownership"))

        self.assertEqual(result, 0)
        self.assertIn("skipped", output.getvalue())
        self.assertNotIn(str(self.checkout), output.getvalue())

    def test_ownership_success_withholds_output_and_scrubs_python_state(self) -> None:
        caller_home = self.root / "caller-home"
        caller_home.mkdir()
        self._module(
            "check_target_ownership",
            f"""
            import os
            from pathlib import Path
            import sys

            assert sys.argv[1:] == ["--public-targets", {str(self.manifest.resolve())!r}]
            assert "PYTHONPATH" not in os.environ
            assert "VIRTUAL_ENV" not in os.environ
            assert "GIT_INDEX_FILE" not in os.environ
            isolated_paths = [
                Path(os.environ[name])
                for name in (
                    "HOME",
                    "XDG_CACHE_HOME",
                    "XDG_CONFIG_HOME",
                    "XDG_DATA_HOME",
                    "XDG_STATE_HOME",
                )
            ]
            assert all(path.is_dir() for path in isolated_paths)
            assert len({{path.parent for path in isolated_paths}}) == 1
            assert isolated_paths[0] != Path({str(caller_home)!r})
            (Path.home() / "companion-attempt").write_text("isolated", encoding="utf-8")
            print({PRIVATE_SENTINEL!r})
            """,
        )
        output = io.StringIO()
        environment = {
            "DOTFILES_PRIVATE_DIR": str(self.checkout),
            "PYTHONPATH": str(self.root / "shadow"),
            "VIRTUAL_ENV": str(self.root / "venv"),
            "GIT_INDEX_FILE": str(self.root / "foreign-index"),
            "HOME": str(caller_home),
            "XDG_CACHE_HOME": str(caller_home / "cache"),
            "XDG_CONFIG_HOME": str(caller_home / "config"),
            "XDG_DATA_HOME": str(caller_home / "data"),
            "XDG_STATE_HOME": str(caller_home / "state"),
        }
        with mock.patch.dict(os.environ, environment, clear=False), redirect_stdout(output):
            result = bridge.main(self._main_arguments("ownership"))

        self.assertEqual(result, 0)
        self.assertIn("passed", output.getvalue())
        self.assertNotIn(PRIVATE_SENTINEL, output.getvalue())
        self.assertFalse((caller_home / "companion-attempt").exists())
        self.assertNotIn(
            str(self.checkout),
            self.session_state.read_text(encoding="ascii"),
        )
        self.assertEqual(self.session_state.stat().st_mode & 0o777, 0o600)

    def test_session_state_fails_closed_without_overwriting_existing_data(self) -> None:
        self.session_state.write_text("malformed", encoding="ascii")
        self.session_state.chmod(0o600)
        with self.assertRaisesRegex(bridge.BridgeError, "state is invalid"):
            bridge._read_session_state(self.session_state)

        self.session_state.write_text("public-only\n", encoding="ascii")
        self.session_state.chmod(0o644)
        with self.assertRaisesRegex(bridge.BridgeError, "state is unsafe"):
            bridge._read_session_state(self.session_state)

        self.session_state.unlink()
        symlink_target = self.root / "foreign-state"
        symlink_target.write_text("public-only\n", encoding="ascii")
        self.session_state.symlink_to(symlink_target)
        with self.assertRaisesRegex(bridge.BridgeError, "state is unavailable"):
            bridge._read_session_state(self.session_state)

        self.session_state.unlink()
        self.session_state.write_text("preserve me\n", encoding="ascii")
        with self._environment(), self.assertRaisesRegex(
            bridge.BridgeError, "state already exists"
        ):
            bridge.run("ownership", self.session_state, self.manifest)
        self.assertEqual(
            self.session_state.read_text(encoding="ascii"),
            "preserve me\n",
        )

    def test_private_failure_withholds_stdout_and_stderr(self) -> None:
        self._module(
            "check_private_source",
            f"""
            import sys
            print({PRIVATE_SENTINEL!r})
            print({PRIVATE_SENTINEL!r}, file=sys.stderr)
            raise SystemExit(23)
            """,
        )
        self._authorize_source()
        error = io.StringIO()
        with self._environment(), redirect_stderr(error):
            result = bridge.main(self._main_arguments("source"))

        self.assertEqual(result, 1)
        self.assertIn("status 23", error.getvalue())
        self.assertNotIn(PRIVATE_SENTINEL, error.getvalue())

    def test_operating_system_error_withholds_private_path(self) -> None:
        self._module("check_private_source", "")
        self._authorize_source()
        error = io.StringIO()
        launch_error = OSError(13, "Permission denied", str(self.checkout))
        with (
            self._environment(),
            mock.patch.object(bridge.subprocess, "Popen", side_effect=launch_error),
            redirect_stderr(error),
        ):
            result = bridge.main(self._main_arguments("source"))

        self.assertEqual(result, 1)
        self.assertEqual(
            error.getvalue(),
            "companion chezmoi: companion check could not complete; details withheld\n",
        )
        self.assertNotIn(str(self.checkout), error.getvalue())

    def test_resolution_error_withholds_private_path(self) -> None:
        self._module("check_private_source", "")
        self._authorize_source()
        error = io.StringIO()
        resolution_error = RuntimeError(f"Symlink loop from {self.checkout}")
        with (
            self._environment(),
            mock.patch.object(Path, "resolve", side_effect=resolution_error),
            redirect_stderr(error),
        ):
            result = bridge.main(self._main_arguments("source"))

        self.assertEqual(result, 1)
        self.assertEqual(
            error.getvalue(),
            "companion chezmoi: companion checkout path cannot be resolved\n",
        )
        self.assertNotIn(str(self.checkout), error.getvalue())

    def test_timeout_terminates_the_private_process_group(self) -> None:
        child_pid_file = self.root / "child.pid"
        self._module(
            "check_private_source",
            f"""
            import os
            from pathlib import Path
            import subprocess
            import sys
            import time

            child = subprocess.Popen(
                [
                    sys.executable,
                    "-c",
                    "import os, signal, time; "
                    "signal.signal(signal.SIGTERM, signal.SIG_IGN); "
                    "open(os.environ['BRIDGE_CHILD_PID_FILE'], 'w').write(str(os.getpid())); "
                    "time.sleep(60)",
                ],
                env={{**os.environ, "BRIDGE_CHILD_PID_FILE": {str(child_pid_file)!r}}},
            )
            while not Path({str(child_pid_file)!r}).exists():
                if child.poll() is not None:
                    raise SystemExit("fixture child exited before becoming ready")
                time.sleep(0.01)
            time.sleep(60)
            """,
        )
        started = time.monotonic()
        with self._environment(), self.assertRaisesRegex(
            bridge.BridgeError, "bounded deadline"
        ):
            bridge._invoke_private(
                self.checkout,
                bridge.PRIVATE_MODULES["source"],
                [],
                timeout=0.2,
            )

        self.assertLess(time.monotonic() - started, 3)
        child_pid = int(child_pid_file.read_text(encoding="utf-8"))
        deadline = time.monotonic() + 1
        while True:
            try:
                os.kill(child_pid, 0)
            except ProcessLookupError:
                break
            if time.monotonic() >= deadline:
                self.fail("timeout cleanup left a SIGTERM-ignoring descendant")
            time.sleep(0.01)

    def test_completed_check_terminates_remaining_descendants(self) -> None:
        child_pid_file = self.root / "completed-child.pid"
        self._module(
            "check_private_source",
            f"""
            import os
            from pathlib import Path
            import subprocess
            import sys
            import time

            child = subprocess.Popen(
                [
                    sys.executable,
                    "-c",
                    "import os, signal, time; "
                    "signal.signal(signal.SIGTERM, signal.SIG_IGN); "
                    "open(os.environ['BRIDGE_CHILD_PID_FILE'], 'w').write(str(os.getpid())); "
                    "time.sleep(60)",
                ],
                env={{**os.environ, "BRIDGE_CHILD_PID_FILE": {str(child_pid_file)!r}}},
            )
            while not Path({str(child_pid_file)!r}).exists():
                if child.poll() is not None:
                    raise SystemExit("fixture child exited before becoming ready")
                time.sleep(0.01)
            """,
        )

        started = time.monotonic()
        with self._environment():
            bridge._invoke_private(
                self.checkout,
                bridge.PRIVATE_MODULES["source"],
                [],
                timeout=2,
            )

        self.assertLess(time.monotonic() - started, 3)
        child_pid = int(child_pid_file.read_text(encoding="utf-8"))
        deadline = time.monotonic() + 1
        while True:
            try:
                os.kill(child_pid, 0)
            except ProcessLookupError:
                break
            if time.monotonic() >= deadline:
                self.fail("completed-check cleanup left a descendant running")
            time.sleep(0.01)

    def test_cleanup_bounds_wait_after_sigkill(self) -> None:
        process = mock.Mock()
        process.pid = 123

        with (
            mock.patch.object(bridge.os, "killpg") as killpg,
            mock.patch.object(bridge.time, "sleep") as sleep,
        ):
            bridge._stop_process_group(process)

        self.assertEqual(
            killpg.call_args_list,
            [
                mock.call(process.pid, bridge.signal.SIGTERM),
                mock.call(process.pid, bridge.signal.SIGKILL),
            ],
        )
        sleep.assert_called_once_with(bridge.CLEANUP_TERM_GRACE_SECONDS)
        process.wait.assert_called_once_with(timeout=bridge.CLEANUP_TIMEOUT_SECONDS)

    def test_completion_wait_is_bounded_and_does_not_reap_the_leader(self) -> None:
        process = mock.Mock()
        process.pid = 123
        with (
            mock.patch.object(bridge.os, "waitid", return_value=None) as waitid,
            mock.patch.object(bridge.time, "monotonic", side_effect=[10, 13]),
        ):
            completed = bridge._wait_without_reaping(process, timeout=2)

        self.assertFalse(completed)
        waitid.assert_called_once_with(
            bridge.os.P_PID,
            process.pid,
            bridge.os.WEXITED | bridge.os.WNOHANG | bridge.os.WNOWAIT,
        )
        process.wait.assert_not_called()

    def test_non_directory_and_stale_checkout_fail_generically(self) -> None:
        self.checkout.write_text(PRIVATE_SENTINEL, encoding="utf-8")
        with self._environment(), self.assertRaisesRegex(
            bridge.BridgeError, "not a directory"
        ):
            bridge.run("ownership", self.session_state, self.manifest)

        self.checkout.unlink()
        self.checkout.mkdir()
        with self._environment(), self.assertRaisesRegex(
            bridge.BridgeError, "incompatible"
        ):
            bridge.run("ownership", self.session_state, self.manifest)

    def test_source_rejects_checkout_removed_after_ownership(self) -> None:
        self._module("check_private_source", "")
        self._authorize_source()
        moved_checkout = self.root / "moved-companion"
        self.checkout.rename(moved_checkout)

        with self._environment(), self.assertRaisesRegex(
            bridge.BridgeError, "changed during canary"
        ):
            bridge.run("source", self.session_state)

    def test_source_rejects_checkout_replaced_after_ownership(self) -> None:
        self._module("check_private_source", "")
        self._authorize_source()
        moved_checkout = self.root / "original-companion"
        self.checkout.rename(moved_checkout)
        self._module("check_private_source", "")

        with self._environment(), self.assertRaisesRegex(
            bridge.BridgeError, "changed during canary"
        ):
            bridge.run("source", self.session_state)

    def test_public_only_session_rejects_a_late_companion(self) -> None:
        with self._environment():
            result = bridge.run("ownership", self.session_state, self.manifest)
        self.assertEqual(result, "skipped")
        self._module("check_private_source", "")

        with self._environment(), self.assertRaisesRegex(
            bridge.BridgeError, "changed during canary"
        ):
            bridge.run("source", self.session_state)


if __name__ == "__main__":
    unittest.main()
