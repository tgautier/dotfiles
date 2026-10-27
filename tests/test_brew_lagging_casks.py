from __future__ import annotations

import contextlib
import importlib.machinery
import importlib.util
import io
import json
from pathlib import Path
import plistlib
import sys
import tempfile
import textwrap
import unittest


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "bin/brew-lagging-casks"
LOADER = importlib.machinery.SourceFileLoader("brew_lagging_casks_tests", str(SCRIPT_PATH))
SPEC = importlib.util.spec_from_loader(LOADER.name, LOADER)
if SPEC is None:
    raise RuntimeError("could not load brew-lagging-casks module")
LAGGING = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = LAGGING
LOADER.exec_module(LAGGING)


class VersionTests(unittest.TestCase):
    def test_cask_build_suffix_is_ignored(self) -> None:
        self.assertEqual(LAGGING.version_numbers("2.13.0,6362815968182272"), (2, 13, 0))
        self.assertEqual(LAGGING.version_numbers("0.4.24+1"), (0, 4, 24, 1))
        self.assertEqual(LAGGING.version_numbers("latest"), ())

    def test_is_behind_compares_numerically(self) -> None:
        self.assertTrue(LAGGING.is_behind((1, 13, 7), (1, 14, 5)))
        self.assertTrue(LAGGING.is_behind((1, 100), (2, 0, 4)))
        self.assertFalse(LAGGING.is_behind((1, 14, 5), (1, 14, 5)))
        self.assertFalse(LAGGING.is_behind((1, 15), (1, 14, 5)))

    def test_shortened_bundle_version_counts_as_current(self) -> None:
        self.assertFalse(LAGGING.is_behind((2026, 1), (2026, 1, 3, 8)))
        self.assertTrue(LAGGING.is_behind((2026, 1), (2026, 2, 1, 8)))


class ReportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def app(self, name: str, info: object) -> str:
        contents = self.root / f"{name}.app/Contents"
        contents.mkdir(parents=True)
        with (contents / "Info.plist").open("wb") as handle:
            plistlib.dump(info, handle)
        return str(self.root / f"{name}.app")

    def cask(self, token: str, version: str, target: str | None, auto_updates: bool = True) -> dict:
        artifacts: list[dict] = [{"uninstall": [{"quit": token}]}]
        if target is not None:
            artifacts.append({"app": [Path(target).name], "target": target})
        return {"token": token, "version": version, "auto_updates": auto_updates, "artifacts": artifacts}

    def test_reports_only_auto_updating_apps_behind_the_tap(self) -> None:
        casks = [
            self.cask("obsidian", "1.14.5", self.app("Obsidian", {"CFBundleShortVersionString": "1.13.7"})),
            self.cask("current", "2.0.0,99", self.app("Current", {"CFBundleShortVersionString": "2.0.0"})),
            self.cask("ahead", "3.0.0", self.app("Ahead", {"CFBundleShortVersionString": "3.1.0"})),
            self.cask("plain", "9.0.0", self.app("Plain", {"CFBundleShortVersionString": "1.0.0"}), auto_updates=False),
            self.cask("fallback", "5.0.0", self.app("Fallback", {"CFBundleVersion": "4.9"})),
        ]
        report = LAGGING.build_report(casks)
        self.assertEqual(
            report.lagging,
            [
                LAGGING.Lagging("fallback", "4.9", "5.0.0"),
                LAGGING.Lagging("obsidian", "1.13.7", "1.14.5"),
            ],
        )
        self.assertEqual(report.unchecked, [])

    def test_casks_without_a_comparable_bundle_are_listed_as_unchecked(self) -> None:
        casks = [
            self.cask("installer", "1.0.0", None),
            self.cask("latest", "latest", self.app("Latest", {"CFBundleShortVersionString": "1.0"})),
            self.cask("missing", "1.0.0", str(self.root / "Missing.app")),
            self.cask("textual", "1.0.0", self.app("Textual", {"CFBundleShortVersionString": "beta"})),
            self.cask("not-a-dict", "1.0.0", self.app("NotADict", ["1.0"])),
        ]
        report = LAGGING.build_report(casks)
        self.assertEqual(report.lagging, [])
        self.assertEqual(report.unchecked, ["installer", "latest", "missing", "not-a-dict", "textual"])

    def test_render_names_the_upgrade_command(self) -> None:
        output = LAGGING.render(LAGGING.Report([LAGGING.Lagging("obsidian", "1.13.7", "1.14.5")], ["fonts"]))
        self.assertIn("obsidian  1.13.7 -> 1.14.5", output)
        self.assertIn("brew upgrade --cask <cask>", output)
        self.assertIn("Not checked (no comparable app version): fonts", output)
        self.assertIn("matches Homebrew", LAGGING.render(LAGGING.Report([], [])))


class MainTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.calls = self.root / "calls"

    def fake_brew(self, body: str) -> str:
        brew = self.root / "brew"
        brew.write_text(
            textwrap.dedent(
                f"""\
                #!/bin/sh
                printf '%s\\n' "$*" >> {str(self.calls)!r}
                {body}
                """
            ),
            encoding="utf-8",
        )
        brew.chmod(0o755)
        return str(brew)

    def run_main(self, brew: str, platform: str = "darwin") -> tuple[int, str, str]:
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            status = LAGGING.main(["--brew", brew], platform=platform)
        return status, stdout.getvalue(), stderr.getvalue()

    def test_queries_installed_casks_read_only(self) -> None:
        app = self.root / "Obsidian.app/Contents"
        app.mkdir(parents=True)
        with (app / "Info.plist").open("wb") as handle:
            plistlib.dump({"CFBundleShortVersionString": "1.13.7"}, handle)
        payload = {
            "formulae": [],
            "casks": [
                {
                    "token": "obsidian",
                    "version": "1.14.5",
                    "auto_updates": True,
                    "artifacts": [{"app": ["Obsidian.app"], "target": str(self.root / "Obsidian.app")}],
                }
            ],
        }
        (self.root / "payload.json").write_text(json.dumps(payload), encoding="utf-8")
        status, stdout, stderr = self.run_main(self.fake_brew(f"cat {str(self.root / 'payload.json')!r}"))
        self.assertEqual(status, 0, stderr)
        self.assertIn("obsidian  1.13.7 -> 1.14.5", stdout)
        self.assertEqual(self.calls.read_text(encoding="utf-8"), "info --cask --installed --json=v2\n")

    def test_brew_failure_is_reported_and_fails(self) -> None:
        status, stdout, stderr = self.run_main(self.fake_brew("echo boom >&2; exit 3"))
        self.assertEqual(status, 1)
        self.assertEqual(stdout, "")
        self.assertIn("could not list installed casks", stderr)

    def test_malformed_json_is_reported_and_fails(self) -> None:
        for body in ("echo not-json", "echo '{\"casks\": {}}'"):
            with self.subTest(body=body):
                status, _, stderr = self.run_main(self.fake_brew(body))
                self.assertEqual(status, 1)
                self.assertIn("could not list installed casks", stderr)

    def test_other_platforms_skip_without_calling_brew(self) -> None:
        status, stdout, _ = self.run_main(self.fake_brew("exit 9"), platform="linux")
        self.assertEqual(status, 0)
        self.assertIn("only on macOS", stdout)
        self.assertFalse(self.calls.exists())


if __name__ == "__main__":
    unittest.main()
