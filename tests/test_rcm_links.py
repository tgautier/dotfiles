from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPOSITORY = Path(__file__).resolve().parent.parent
PROGRAM = REPOSITORY / "bin/rcm-links"


class RcmLinksInventoryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not (REPOSITORY / "Justfile").is_file() or not PROGRAM.is_file():
            raise RuntimeError(f"test repository root is invalid: {REPOSITORY}")

    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.home = self.root / "home"
        self.public = self.root / "public"
        self.private = self.root / "private"
        self.home.mkdir()
        self.public.mkdir()
        self.private.mkdir()
        (self.public / "rcrc").write_text("\n", encoding="utf-8")
        contaminated_git_environment = {
            "GIT_DIR": str(self.root / "leaked.git"),
            "GIT_INDEX_FILE": str(self.root / "leaked.index"),
            "GIT_WORK_TREE": str(self.root / "leaked-work-tree"),
        }
        with mock.patch.dict(os.environ, contaminated_git_environment):
            self._initialize_repository(self.public)
            self._initialize_repository(self.private)

        self.owners = self.root / "owners.tsv"
        self.owners.write_text(
            "owner\ttarget\tsource_root\tsource\n"
            "private-hooks\t.codex/hooks.json\tprivate\tcodex/hooks.json\n"
            "private-skills\t.agents/skills/*\tprivate\tagents/skills/*\n",
            encoding="utf-8",
        )
        self.fake_lsrc = self.root / "fake-lsrc"
        self.fake_lsrc.write_text(
            f"#!{sys.executable}\n"
            "import os\n"
            "from pathlib import Path\n"
            "home = Path(os.environ['HOME'])\n"
            "public = Path(os.environ['DOTFILES_DIR'])\n"
            "print(f\"{home / '.zshrc'}:{public / 'zshrc'}\")\n"
            "print(f\"{home / '.missing'}:{public / 'missing'}\")\n",
            encoding="utf-8",
        )
        self.fake_lsrc.chmod(0o755)

    def _git(self, repository: Path, *arguments: str) -> str:
        environment = {
            name: value for name, value in os.environ.items() if not name.startswith("GIT_")
        }
        completed = subprocess.run(
            ["git", *arguments],
            cwd=repository,
            check=False,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return completed.stdout

    def _initialize_repository(self, repository: Path) -> None:
        self._git(repository, "init", "-q")
        git_directory = Path(self._git(repository, "rev-parse", "--absolute-git-dir").strip()).resolve()
        self.assertTrue(git_directory.is_relative_to(repository.resolve()), git_directory)

    def _commit(self, repository: Path, message: str) -> None:
        self._git(repository, "add", "--all")
        self._git(
            repository,
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "-c",
            "commit.gpgsign=false",
            "commit",
            "-q",
            "-m",
            message,
        )

    def _write(self, repository: Path, relative: str, content: str = "fixture\n") -> Path:
        path = repository / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def _link(self, relative: str, target: Path | str) -> Path:
        path = self.home / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.symlink_to(target)
        return path

    def _inventory(self, *, owners: Path | None = None) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment.update(
            {
                "GIT_DIR": str(self.root / "leaked.git"),
                "GIT_INDEX_FILE": str(self.root / "leaked.index"),
                "GIT_WORK_TREE": str(self.root / "leaked-work-tree"),
            }
        )
        return subprocess.run(
            [
                sys.executable,
                str(PROGRAM),
                "inventory",
                "--home",
                str(self.home),
                "--public-dir",
                str(self.public),
                "--private-dir",
                str(self.private),
                "--owners",
                str(owners or self.owners),
                "--lsrc",
                str(self.fake_lsrc),
                "--format",
                "json",
            ],
            cwd=REPOSITORY,
            check=False,
            env=environment,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
        )

    def test_inventory_classifies_current_historical_and_dedicated_links(self) -> None:
        zshrc = self._write(self.public, "zshrc")
        self._write(self.public, "missing")
        excluded = self._write(self.public, "docs/excluded.md")
        removed = self._write(self.private, "removed/old")
        hook = self._write(self.private, "codex/hooks.json", "{}\n")
        skill = self._write(self.private, "agents/skills/example/SKILL.md")
        self._commit(self.public, "add public sources")
        self._commit(self.private, "add private sources")
        removed.unlink()
        self._commit(self.private, "remove former source root")

        self._link(".zshrc", zshrc)
        self._link(".docs/excluded.md", excluded)
        self._link(".removed/old", removed)
        self._link(".codex/hooks.json", hook)
        self._link(".agents/skills/example", skill.parent)
        self._link(".agents/skills/removed", self.private / "agents/skills/removed")
        self._link(".docs/external", self.root / "archive/dotfiles/external")

        completed = self._inventory()
        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["schema"], 1)
        records = {record["target"]: record for record in payload["records"]}

        self.assertEqual((records[".zshrc"]["disposition"], records[".zshrc"]["status"]), ("rcm", "linked"))
        self.assertEqual((records[".missing"]["disposition"], records[".missing"]["status"]), ("rcm", "missing"))
        self.assertEqual(
            (records[".docs/excluded.md"]["disposition"], records[".docs/excluded.md"]["status"]),
            ("obsolete", "linked"),
        )
        self.assertEqual(
            (records[".removed/old"]["disposition"], records[".removed/old"]["status"]),
            ("obsolete", "broken"),
        )
        self.assertEqual(records[".codex/hooks.json"]["disposition"], "dedicated")
        self.assertEqual(records[".agents/skills/example"]["disposition"], "dedicated")
        self.assertEqual(
            (records[".agents/skills/removed"]["disposition"], records[".agents/skills/removed"]["status"]),
            ("obsolete", "broken"),
        )
        self.assertEqual(records[".docs/external"]["disposition"], "unclassified")

    def test_changed_declared_link_and_regular_collision_fail_closed(self) -> None:
        self._write(self.public, "zshrc")
        self._write(self.public, "missing")
        self._commit(self.public, "add declared sources")
        self._write(self.private, "placeholder")
        self._commit(self.private, "add placeholder")
        self._link(".zshrc", self.root / "foreign")
        (self.home / ".missing").write_text("collision\n", encoding="utf-8")

        completed = self._inventory()
        self.assertEqual(completed.returncode, 0, completed.stderr)
        records = {record["target"]: record for record in json.loads(completed.stdout)["records"]}
        self.assertEqual(
            (records[".zshrc"]["disposition"], records[".zshrc"]["status"]),
            ("unclassified", "changed"),
        )
        self.assertEqual(
            (records[".missing"]["disposition"], records[".missing"]["status"]),
            ("unclassified", "collision"),
        )

    def test_malformed_owner_manifest_stops_before_inventory(self) -> None:
        self._write(self.public, "zshrc")
        self._write(self.public, "missing")
        self._commit(self.public, "add public sources")
        self._write(self.private, "placeholder")
        self._commit(self.private, "add placeholder")
        malformed = self.root / "malformed.tsv"
        malformed.write_text(
            "owner\ttarget\tsource_root\tsource\n"
            "bad\t.agents/skills/*\tprivate\tagents/skills/not-wildcard\n",
            encoding="utf-8",
        )

        completed = self._inventory(owners=malformed)
        self.assertEqual(completed.returncode, 2)
        self.assertIn("target/source wildcard mismatch", completed.stderr)
        self.assertEqual(completed.stdout, "")


if __name__ == "__main__":
    unittest.main()
