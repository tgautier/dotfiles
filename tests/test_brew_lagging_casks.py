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
from typing import Sequence
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
        # Joined rather than dedented: a multi-line body would defeat dedent.
        header = f"#!/bin/sh\nprintf '%s\\n' \"$*\" >> {str(self.calls)!r}\n"
        brew.write_text(header + body + "\n", encoding="utf-8")
        brew.chmod(0o755)
        return str(brew)

    def run_main(
        self,
        brew: str,
        platform: str = "darwin",
        extra: Sequence[str] = (),
        interactive: bool | None = False,
        answer: str | None = None,
    ) -> tuple[int, str, str]:
        prompts: list[str] = []

        def ask(prompt: str) -> str:
            prompts.append(prompt)
            if answer is None:
                raise EOFError
            return answer

        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            status = LAGGING.main(["--brew", brew, *extra], platform=platform, interactive=interactive, ask=ask)
        self.prompts = prompts
        return status, stdout.getvalue(), stderr.getvalue()

    def write_payload(self, name: str, tap_version: str) -> Path:
        payload = {
            "formulae": [],
            "casks": [
                {
                    "token": "obsidian",
                    "version": tap_version,
                    "auto_updates": True,
                    "artifacts": [{"app": ["Obsidian.app"], "target": str(self.root / "Obsidian.app")}],
                }
            ],
        }
        path = self.root / name
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def lagging_brew(self, upgrade_status: int = 0, catches_up: bool = True) -> str:
        """Fake brew with one app behind; `upgrade` optionally brings it level."""
        app = self.root / "Obsidian.app/Contents"
        app.mkdir(parents=True)
        with (app / "Info.plist").open("wb") as handle:
            plistlib.dump({"CFBundleShortVersionString": "1.13.7"}, handle)
        current = self.write_payload("payload.json", "1.14.5")
        after = self.write_payload("after.json", "1.13.7" if catches_up else "1.14.5")
        return self.fake_brew(
            textwrap.dedent(
                f"""                case "$1" in
                    info) cat {str(current)!r} ;;
                    upgrade) cp {str(after)!r} {str(current)!r}; exit {upgrade_status} ;;
                    *) exit 9 ;;
                esac
                """
            )
        )

    def calls_made(self) -> list[str]:
        return self.calls.read_text(encoding="utf-8").splitlines()

    def test_queries_installed_casks_read_only(self) -> None:
        status, stdout, stderr = self.run_main(self.lagging_brew(), interactive=True, answer="y")
        self.assertEqual(status, 0, stderr)
        self.assertIn("obsidian  1.13.7 -> 1.14.5", stdout)
        self.assertEqual(self.prompts, [])
        self.assertEqual(self.calls_made(), ["info --cask --installed --json=v2"])

    def test_yes_upgrades_the_listed_casks_and_rechecks(self) -> None:
        for answer in ("y", "YES", " yes \n"):
            with self.subTest(answer=answer):
                self.setUp()
                status, stdout, stderr = self.run_main(
                    self.lagging_brew(), extra=["--offer-upgrade"], interactive=True, answer=answer
                )
                self.assertEqual(status, 0, stderr)
                self.assertEqual(len(self.prompts), 1)
                self.assertIn("Upgrade this 1 app through Homebrew?", self.prompts[0])
                self.assertIn("quit and reopened", self.prompts[0])
                self.assertEqual(
                    self.calls_made(),
                    [
                        "info --cask --installed --json=v2",
                        "upgrade --cask obsidian",
                        "info --cask --installed --json=v2",
                    ],
                )
                self.assertIn("Every upgraded app now matches Homebrew.", stdout)

    def test_anything_but_yes_upgrades_nothing(self) -> None:
        for answer in ("", "n", "no", "yep", None):
            with self.subTest(answer=answer):
                self.setUp()
                status, stdout, stderr = self.run_main(
                    self.lagging_brew(), extra=["--offer-upgrade"], interactive=True, answer=answer
                )
                self.assertEqual(status, 0, stderr)
                self.assertEqual(len(self.prompts), 1)
                self.assertIn("Nothing upgraded.", stdout)
                self.assertEqual(self.calls_made(), ["info --cask --installed --json=v2"])

    def test_no_terminal_skips_the_prompt(self) -> None:
        status, stdout, stderr = self.run_main(self.lagging_brew(), extra=["--offer-upgrade"], interactive=False)
        self.assertEqual(status, 0, stderr)
        self.assertEqual(self.prompts, [])
        self.assertIn("nothing was upgraded", stdout)
        self.assertEqual(self.calls_made(), ["info --cask --installed --json=v2"])

    def test_nothing_lagging_asks_nothing(self) -> None:
        brew = self.fake_brew("echo '{\"formulae\": [], \"casks\": []}'")
        status, stdout, stderr = self.run_main(brew, extra=["--offer-upgrade"], interactive=True, answer="y")
        self.assertEqual(status, 0, stderr)
        self.assertEqual(self.prompts, [])
        self.assertIn("matches Homebrew", stdout)
        self.assertEqual(self.calls_made(), ["info --cask --installed --json=v2"])

    def test_failed_upgrade_fails_and_still_rechecks(self) -> None:
        status, stdout, _ = self.run_main(
            self.lagging_brew(upgrade_status=1, catches_up=False),
            extra=["--offer-upgrade"],
            interactive=True,
            answer="y",
        )
        self.assertEqual(status, 1)
        self.assertEqual(len(self.calls_made()), 3)
        self.assertIn("Still behind after the upgrade: obsidian", stdout)

    def test_prompt_counts_several_apps(self) -> None:
        prompts: list[str] = []
        self.assertFalse(LAGGING.confirm_upgrade(18, lambda prompt: prompts.append(prompt) or "n"))
        self.assertTrue(prompts[0].startswith("Upgrade these 18 apps through Homebrew?"))
        self.assertTrue(prompts[0].endswith("[y/N] "))

    def test_skipped_upgrade_names_the_reinstall_remedy(self) -> None:
        status, stdout, _ = self.run_main(
            self.lagging_brew(catches_up=False), extra=["--offer-upgrade"], interactive=True, answer="y"
        )
        self.assertEqual(status, 0)
        self.assertIn("Still behind after the upgrade: obsidian", stdout)
        self.assertIn("brew reinstall --cask obsidian", stdout)

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
