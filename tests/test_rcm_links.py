from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path, PurePosixPath
from types import ModuleType
from unittest import mock


REPOSITORY = Path(__file__).resolve().parent.parent
PROGRAM = REPOSITORY / "bin/rcm-links"


def load_program_module() -> ModuleType:
    module_name = "rcm_links_under_test"
    loader = SourceFileLoader(module_name, str(PROGRAM))
    specification = importlib.util.spec_from_loader(module_name, loader)
    if specification is None or specification.loader is None:
        raise RuntimeError(f"cannot load inventory helper: {PROGRAM}")
    module = importlib.util.module_from_spec(specification)
    sys.modules[module_name] = module
    specification.loader.exec_module(module)
    return module


RCM_LINKS = load_program_module()


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

    def _command(
        self,
        command: str,
        *arguments: str,
        owners: Path | None = None,
    ) -> subprocess.CompletedProcess[str]:
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
                command,
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
                *arguments,
            ],
            cwd=REPOSITORY,
            check=False,
            env=environment,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
        )

    def _inventory(self, *, owners: Path | None = None) -> subprocess.CompletedProcess[str]:
        return self._command("inventory", "--format", "json", owners=owners)

    def _cleanup_plan(self) -> subprocess.CompletedProcess[str]:
        return self._command("plan")

    def _cleanup(self, plan: Path, digest: str) -> subprocess.CompletedProcess[str]:
        return self._command("cleanup", "--plan", str(plan), "--confirm", digest)

    def _restore(self, plan: Path, digest: str) -> subprocess.CompletedProcess[str]:
        return self._command("restore", "--plan", str(plan), "--confirm", digest)

    @staticmethod
    def _plan_digest(payload: dict[str, object]) -> str:
        digest_payload = {key: value for key, value in payload.items() if key != "approval_sha256"}
        encoded = json.dumps(
            digest_payload,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

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
        hook = self._write(self.private, "codex/hooks.json", "{}\n")
        self._write(self.private, "agents/skills/example/SKILL.md")
        self._commit(self.private, "add dedicated source")
        self._link(".zshrc", self.root / "foreign")
        (self.home / ".missing").write_text("collision\n", encoding="utf-8")
        (self.home / ".agents").write_text("blocking ancestor\n", encoding="utf-8")
        external_codex = self.root / "external-codex"
        external_codex.mkdir()
        (external_codex / "hooks.json").symlink_to(hook)
        self._link(".codex", external_codex)

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
        self.assertEqual(
            (
                records[".agents/skills/example"]["disposition"],
                records[".agents/skills/example"]["status"],
            ),
            ("unclassified", "collision"),
        )
        self.assertEqual(
            (
                records[".codex/hooks.json"]["disposition"],
                records[".codex/hooks.json"]["status"],
            ),
            ("unclassified", "collision"),
        )

    def test_inventory_refuses_untracked_exact_dedicated_source(self) -> None:
        self._write(self.public, "zshrc")
        self._write(self.public, "missing")
        hook = self._write(self.private, "codex/hooks.json", "{}\n")
        self._commit(self.public, "add public sources")
        self._commit(self.private, "add exact dedicated source")
        hook.unlink()
        self._commit(self.private, "remove exact dedicated source")
        self._link(".codex/hooks.json", hook)

        completed = self._inventory()
        self.assertEqual(completed.returncode, 2)
        self.assertIn("dedicated-owner source is not tracked", completed.stderr)
        self.assertEqual(completed.stdout, "")

    def test_inventory_refuses_unavailable_exact_owner_repository(self) -> None:
        self._write(self.public, "zshrc")
        self._write(self.public, "missing")
        self._commit(self.public, "add public sources")
        self._write(self.private, "codex/hooks.json", "{}\n")
        self._commit(self.private, "add exact dedicated source")
        self.private.rename(self.root / "unavailable-private")

        completed = self._inventory()
        self.assertEqual(completed.returncode, 2)
        self.assertIn("dedicated-owner repository is unavailable", completed.stderr)
        self.assertEqual(completed.stdout, "")

    def test_inventory_refuses_shallow_repository(self) -> None:
        self._write(self.public, "zshrc")
        self._write(self.public, "missing")
        self._commit(self.public, "add public sources")
        self._write(self.public, "second-commit")
        self._commit(self.public, "add second public commit")
        self._write(self.private, "codex/hooks.json", "{}\n")
        self._commit(self.private, "add exact dedicated source")
        shallow_public = self.root / "shallow-public"
        self._git(
            self.root,
            "clone",
            "-q",
            "--depth",
            "1",
            f"file://{self.public}",
            str(shallow_public),
        )
        self.public = shallow_public

        completed = self._inventory()
        self.assertEqual(completed.returncode, 2)
        self.assertIn("repository is shallow", completed.stderr)
        self.assertEqual(completed.stdout, "")

    def test_inventory_uses_current_head_history_only(self) -> None:
        self._write(self.public, "zshrc")
        self._write(self.public, "missing")
        self._commit(self.public, "add public sources")
        current_branch = self._git(self.public, "branch", "--show-current").strip()
        self._git(self.public, "checkout", "-q", "-b", "unmerged-history")
        branch_only = self._write(self.public, "branch-only/old")
        self._commit(self.public, "add branch-only source")
        self._git(self.public, "checkout", "-q", current_branch)
        self._write(self.private, "codex/hooks.json", "{}\n")
        self._commit(self.private, "add exact dedicated source")
        self._link(".branch-only/old", branch_only)

        completed = self._inventory()
        self.assertEqual(completed.returncode, 0, completed.stderr)
        targets = {record["target"] for record in json.loads(completed.stdout)["records"]}
        self.assertNotIn(".branch-only/old", targets)

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

    def test_cleanup_requires_exact_approved_obsolete_links(self) -> None:
        zshrc = self._write(self.public, "zshrc")
        self._write(self.public, "missing")
        excluded = self._write(self.public, "docs/excluded.md")
        hook = self._write(self.private, "codex/hooks.json", "{}\n")
        self._write(self.private, "agents/skills/example/SKILL.md")
        self._commit(self.public, "add public sources")
        self._commit(self.private, "add private sources")

        self._link(".zshrc", zshrc)
        obsolete_linked = self._link(".docs/excluded.md", excluded)
        obsolete_broken = self._link(
            ".agents/skills/removed",
            self.private / "agents/skills/removed",
        )
        dedicated = self._link(".codex/hooks.json", hook)
        unclassified = self._link(".docs/external", self.root / "external")

        generated = self._cleanup_plan()
        self.assertEqual(generated.returncode, 0, generated.stderr)
        payload = json.loads(generated.stdout)
        self.assertEqual(
            [link["target"] for link in payload["links"]],
            [".agents/skills/removed", ".docs/excluded.md"],
        )
        self.assertEqual(payload["approval_sha256"], self._plan_digest(payload))
        plan = self.root / "cleanup-plan.json"
        plan.write_text(json.dumps(payload), encoding="utf-8")

        wrong_digest = self._cleanup(plan, "0" * 64)
        self.assertEqual(wrong_digest.returncode, 2)
        self.assertIn("--confirm does not match", wrong_digest.stderr)
        self.assertTrue(obsolete_linked.is_symlink())
        self.assertTrue(obsolete_broken.is_symlink())

        unsafe_payload = json.loads(json.dumps(payload))
        unsafe_payload["links"][0]["target"] = "."
        unsafe_payload["approval_sha256"] = self._plan_digest(unsafe_payload)
        plan.write_text(json.dumps(unsafe_payload), encoding="utf-8")
        unsafe = self._cleanup(plan, unsafe_payload["approval_sha256"])
        self.assertEqual(unsafe.returncode, 2)
        self.assertIn("must be a safe relative path", unsafe.stderr)
        self.assertTrue(obsolete_linked.is_symlink())
        self.assertTrue(obsolete_broken.is_symlink())

        tampered_payload = json.loads(json.dumps(payload))
        tampered_payload["links"][0]["link_target"] += ".tampered"
        plan.write_text(json.dumps(tampered_payload), encoding="utf-8")
        tampered = self._cleanup(plan, payload["approval_sha256"])
        self.assertEqual(tampered.returncode, 2)
        self.assertIn("content does not match its approval_sha256", tampered.stderr)
        self.assertTrue(obsolete_linked.is_symlink())
        self.assertTrue(obsolete_broken.is_symlink())

        unclassified_payload = json.loads(json.dumps(payload))
        unclassified_payload["links"].append(
            {
                "target": ".docs/external",
                "link_target": str(self.root / "external"),
            }
        )
        unclassified_payload["approval_sha256"] = self._plan_digest(unclassified_payload)
        plan.write_text(json.dumps(unclassified_payload), encoding="utf-8")
        refused = self._cleanup(plan, unclassified_payload["approval_sha256"])
        self.assertEqual(refused.returncode, 2)
        self.assertIn("is not currently obsolete", refused.stderr)
        self.assertTrue(obsolete_linked.is_symlink())
        self.assertTrue(obsolete_broken.is_symlink())
        self.assertTrue(unclassified.is_symlink())

        plan.write_text(json.dumps(payload), encoding="utf-8")
        obsolete_linked.unlink()
        obsolete_linked.symlink_to(self.private / "other-source")
        changed = self._cleanup(plan, payload["approval_sha256"])
        self.assertEqual(changed.returncode, 2)
        self.assertIn("evidence changed after review", changed.stderr)
        self.assertTrue(obsolete_linked.is_symlink())
        self.assertTrue(obsolete_broken.is_symlink())

        obsolete_linked.unlink()
        obsolete_linked.symlink_to(excluded)
        docs_directory = self.home / ".docs"
        docs_directory.chmod(0o555)
        try:
            partial_cleanup = self._cleanup(plan, payload["approval_sha256"])
        finally:
            docs_directory.chmod(0o755)
        self.assertEqual(partial_cleanup.returncode, 2)
        self.assertIn("stopped after 1 removals", partial_cleanup.stderr)
        self.assertFalse(obsolete_broken.is_symlink())
        self.assertTrue(obsolete_linked.is_symlink())

        cleaned = self._cleanup(plan, payload["approval_sha256"])
        self.assertEqual(cleaned.returncode, 0, cleaned.stderr)
        self.assertEqual(
            cleaned.stdout.splitlines(),
            [
                "already absent\t.agents/skills/removed",
                "removed\t.docs/excluded.md",
                "cleanup complete\tchanged=1\talready_absent=1",
            ],
        )
        self.assertFalse(obsolete_linked.is_symlink())
        self.assertFalse(obsolete_broken.is_symlink())
        self.assertTrue((self.home / ".zshrc").is_symlink())
        self.assertTrue(dedicated.is_symlink())
        self.assertTrue(unclassified.is_symlink())

        after = self._inventory()
        self.assertEqual(after.returncode, 0, after.stderr)
        after_records = json.loads(after.stdout)["records"]
        self.assertNotIn("obsolete", {record["disposition"] for record in after_records})

        original_lsrc = self.fake_lsrc.read_text(encoding="utf-8")
        self.fake_lsrc.write_text(
            original_lsrc
            + "print(f\"{home / '.docs/excluded.md'}:{public / 'docs/excluded.md'}\")\n",
            encoding="utf-8",
        )
        newly_owned = self._restore(plan, payload["approval_sha256"])
        self.assertEqual(newly_owned.returncode, 2)
        self.assertIn("present in current inventory (rcm/missing)", newly_owned.stderr)
        self.assertFalse(obsolete_linked.is_symlink())
        self.assertFalse(obsolete_broken.is_symlink())
        self.fake_lsrc.write_text(original_lsrc, encoding="utf-8")

        docs_directory.chmod(0o555)
        try:
            partial_restore = self._restore(plan, payload["approval_sha256"])
        finally:
            docs_directory.chmod(0o755)
        self.assertEqual(partial_restore.returncode, 2)
        self.assertIn("stopped after 1 links", partial_restore.stderr)
        self.assertTrue(obsolete_broken.is_symlink())
        self.assertFalse(obsolete_linked.is_symlink())

        restored = self._restore(plan, payload["approval_sha256"])
        self.assertEqual(restored.returncode, 0, restored.stderr)
        self.assertEqual(
            restored.stdout.splitlines(),
            [
                "already restored\t.agents/skills/removed",
                "restored\t.docs/excluded.md",
                "restore complete\tchanged=1\talready_restored=1",
            ],
        )
        self.assertEqual(os.readlink(obsolete_linked), str(excluded))
        self.assertEqual(
            os.readlink(obsolete_broken),
            str(self.private / "agents/skills/removed"),
        )
        self.assertTrue((self.home / ".zshrc").is_symlink())
        self.assertTrue(dedicated.is_symlink())
        self.assertTrue(unclassified.is_symlink())

        repeated_restore = self._restore(plan, payload["approval_sha256"])
        self.assertEqual(repeated_restore.returncode, 0, repeated_restore.stderr)
        self.assertEqual(
            repeated_restore.stdout.splitlines(),
            [
                "already restored\t.agents/skills/removed",
                "already restored\t.docs/excluded.md",
                "restore complete\tchanged=0\talready_restored=2",
            ],
        )

    def test_cleanup_preserves_an_entry_replaced_before_quarantine(self) -> None:
        approved_target = self.root / "approved-source"
        approved_target.write_text("approved\n", encoding="utf-8")
        victim = self._link(".docs/victim", approved_target)
        approved_link = RCM_LINKS.ApprovedLink(
            PurePosixPath(".docs/victim"),
            str(approved_target),
        )
        plan = RCM_LINKS.CleanupPlan(
            self.home,
            self.public,
            self.private,
            (approved_link,),
            "0" * 64,
        )
        records = [
            RCM_LINKS.LinkRecord(
                "obsolete",
                "linked",
                ".docs/victim",
                str(approved_target),
                None,
                "obsolete",
            )
        ]
        original_rename = os.rename

        def replace_then_rename(
            source: str,
            destination: str,
            *,
            src_dir_fd: int,
            dst_dir_fd: int,
        ) -> None:
            os.unlink(source, dir_fd=src_dir_fd)
            replacement = os.open(
                source,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o600,
                dir_fd=src_dir_fd,
            )
            try:
                os.write(replacement, b"raced replacement\n")
            finally:
                os.close(replacement)
            original_rename(
                source,
                destination,
                src_dir_fd=src_dir_fd,
                dst_dir_fd=dst_dir_fd,
            )

        with mock.patch.object(RCM_LINKS.os, "rename", side_effect=replace_then_rename):
            with self.assertRaisesRegex(
                RCM_LINKS.InventoryError,
                "preserved a raced entry",
            ):
                RCM_LINKS.cleanup_approved_links(
                    plan,
                    records=records,
                    refresh_records=lambda: records,
                )

        self.assertFalse(victim.is_symlink())
        quarantines = list((self.home / ".docs").glob(".rcm-links-quarantine-*"))
        self.assertEqual(len(quarantines), 1)
        preserved = quarantines[0] / "approved-link"
        self.assertTrue(preserved.is_file())
        self.assertEqual(preserved.read_bytes(), b"raced replacement\n")

    def test_mutations_refresh_ownership_before_each_change(self) -> None:
        approved_target = self.root / "approved-source"
        approved_target.write_text("approved\n", encoding="utf-8")
        victim = self._link(".docs/victim", approved_target)
        approved_link = RCM_LINKS.ApprovedLink(
            PurePosixPath(".docs/victim"),
            str(approved_target),
        )
        plan = RCM_LINKS.CleanupPlan(
            self.home,
            self.public,
            self.private,
            (approved_link,),
            "0" * 64,
        )
        obsolete = RCM_LINKS.LinkRecord(
            "obsolete",
            "linked",
            ".docs/victim",
            str(approved_target),
            None,
            "obsolete",
        )
        newly_managed = RCM_LINKS.LinkRecord(
            "rcm",
            "missing",
            ".docs/victim",
            None,
            str(approved_target),
            "rcm",
        )

        with self.assertRaisesRegex(
            RCM_LINKS.InventoryError,
            "changed ownership before cleanup",
        ):
            RCM_LINKS.cleanup_approved_links(
                plan,
                records=[obsolete],
                refresh_records=lambda: [newly_managed],
            )
        self.assertTrue(victim.is_symlink())

        victim.unlink()
        with self.assertRaisesRegex(
            RCM_LINKS.InventoryError,
            "changed ownership before restore",
        ):
            RCM_LINKS.restore_approved_links(
                plan,
                records=[],
                refresh_records=lambda: [newly_managed],
            )
        self.assertFalse(victim.is_symlink())


if __name__ == "__main__":
    unittest.main()
