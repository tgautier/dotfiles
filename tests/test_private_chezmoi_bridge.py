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

    def test_absent_checkout_skips_without_printing_its_path(self) -> None:
        output = io.StringIO()
        with self._environment(), redirect_stdout(output):
            result = bridge.main(["ownership", "--public-targets", str(self.manifest)])

        self.assertEqual(result, 0)
        self.assertIn("skipped", output.getvalue())
        self.assertNotIn(str(self.checkout), output.getvalue())

    def test_ownership_success_withholds_output_and_scrubs_python_state(self) -> None:
        self._module(
            "check_target_ownership",
            f"""
            import os
            import sys

            assert sys.argv[1:] == ["--public-targets", {str(self.manifest.resolve())!r}]
            assert "PYTHONPATH" not in os.environ
            assert "VIRTUAL_ENV" not in os.environ
            assert "GIT_INDEX_FILE" not in os.environ
            print({PRIVATE_SENTINEL!r})
            """,
        )
        output = io.StringIO()
        environment = {
            "DOTFILES_PRIVATE_DIR": str(self.checkout),
            "PYTHONPATH": str(self.root / "shadow"),
            "VIRTUAL_ENV": str(self.root / "venv"),
            "GIT_INDEX_FILE": str(self.root / "foreign-index"),
        }
        with mock.patch.dict(os.environ, environment, clear=False), redirect_stdout(output):
            result = bridge.main(["ownership", "--public-targets", str(self.manifest)])

        self.assertEqual(result, 0)
        self.assertIn("passed", output.getvalue())
        self.assertNotIn(PRIVATE_SENTINEL, output.getvalue())

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
        error = io.StringIO()
        with self._environment(), redirect_stderr(error):
            result = bridge.main(["source"])

        self.assertEqual(result, 1)
        self.assertIn("status 23", error.getvalue())
        self.assertNotIn(PRIVATE_SENTINEL, error.getvalue())

    def test_operating_system_error_withholds_private_path(self) -> None:
        self._module("check_private_source", "")
        error = io.StringIO()
        launch_error = OSError(13, "Permission denied", str(self.checkout))
        with (
            self._environment(),
            mock.patch.object(bridge.subprocess, "Popen", side_effect=launch_error),
            redirect_stderr(error),
        ):
            result = bridge.main(["source"])

        self.assertEqual(result, 1)
        self.assertEqual(
            error.getvalue(),
            "companion chezmoi: companion check could not complete; details withheld\n",
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

    def test_non_directory_and_stale_checkout_fail_generically(self) -> None:
        self.checkout.write_text(PRIVATE_SENTINEL, encoding="utf-8")
        with self._environment(), self.assertRaisesRegex(
            bridge.BridgeError, "not a directory"
        ):
            bridge.run("source")

        self.checkout.unlink()
        self.checkout.mkdir()
        with self._environment(), self.assertRaisesRegex(
            bridge.BridgeError, "incompatible"
        ):
            bridge.run("source")


if __name__ == "__main__":
    unittest.main()
