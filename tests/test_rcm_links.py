from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
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
        private_dir: Path | None = None,
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
                str(private_dir or self.private),
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

    def _configure_cutover_fixture(self) -> tuple[Path, Path]:
        zshrc = self._write(self.public, "zshrc", "public zshrc\n")
        missing = self._write(self.public, "missing", "public second file\n")
        local = self._write(self.private, "zshrc.local", "private zshrc\n")
        (self.public / "rcrc").write_text(
            'DOTFILES_DIRS="${DOTFILES_DIR} ${DOTFILES_PRIVATE_DIR}"\n',
            encoding="utf-8",
        )
        self._commit(self.public, "add cutover fixture")
        self._commit(self.private, "add private cutover fixture")

        public_manifest = self.root / "public-targets.tsv"
        public_manifest.write_text(
            "rcm_source\ttarget\tdisposition\tchezmoi_source\tmode\n"
            "missing\t.missing\tretire-at-cutover\t-\tfile\n"
            "zshrc\t.zshrc\tshadow\tdot_zshrc\tfile\n",
            encoding="utf-8",
        )
        private_manifest = self.root / "private-targets.tsv"
        private_manifest.write_text(
            "rcm_source\ttarget\tcurrent_owner\tdisposition\tfuture_owner\ttarget_shape\tmode\tchezmoi_source\n"
            "zshrc.local\t.zshrc.local\tprivate-rcm\tmigrate\tprivate-chezmoi\tprivate-file\t0600\tprivate_dot_zshrc.local\n",
            encoding="utf-8",
        )
        self._write_fake_lsrc(
            (
                (".missing", missing),
                (".zshrc", zshrc),
                (".zshrc.local", local),
            )
        )
        self._link(".missing", missing)
        self._link(".zshrc", zshrc)
        self._link(".zshrc.local", local)
        return public_manifest, private_manifest

    def _write_fake_lsrc(self, rows: tuple[tuple[str, Path], ...]) -> None:
        serialized = repr(tuple((target, str(source)) for target, source in rows))
        self.fake_lsrc.write_text(
            f"#!{sys.executable}\n"
            "import os\n"
            "from pathlib import Path\n"
            f"rows = {serialized}\n"
            "home = Path(os.environ['HOME'])\n"
            "for target, source in rows:\n"
            "    print(f'{home / target}:{source}')\n",
            encoding="utf-8",
        )
        self.fake_lsrc.chmod(0o755)

    def _cutover_command(
        self,
        command: str,
        public_manifest: Path,
        private_manifest: Path,
        *arguments: str,
        private_dir: Path | None = None,
    ) -> subprocess.CompletedProcess[str]:
        return self._command(
            command,
            "--public-targets",
            str(public_manifest),
            "--private-targets",
            str(private_manifest),
            *arguments,
            private_dir=private_dir,
        )

    def _cutover_backup(
        self,
        public_manifest: Path,
        private_manifest: Path,
        output: Path,
    ) -> subprocess.CompletedProcess[str]:
        return self._cutover_command(
            "cutover-backup",
            public_manifest,
            private_manifest,
            "--output",
            str(output),
        )

    def _retained_command(
        self,
        public_manifest: Path,
        rcup: Path,
    ) -> subprocess.CompletedProcess[str]:
        return self._command(
            "link-retained",
            "--public-targets",
            str(public_manifest),
            "--rcup",
            str(rcup),
        )

    def _retained_fixture(self) -> tuple[Path, Path]:
        self._write(self.public, "Brewfile", "brew fixture\n")
        self._write(self.public, "config/mise/config.toml", "[tools]\n")
        self._write(self.public, "zshrc", "zsh fixture\n")
        manifest = self.root / "retained-targets.tsv"
        manifest.write_text(
            "rcm_source\ttarget\tdisposition\tchezmoi_source\tmode\n"
            "Brewfile\t.Brewfile\tdefer-homebrew-link\t-\tfile\n"
            "config/mise/config.toml\t.config/mise/config.toml\t"
            "defer-machine-overrides\t-\tfile\n"
            "zshrc\t.zshrc\tshadow\tdot_zshrc\tfile\n",
            encoding="utf-8",
        )
        rcup = self.root / "fake-rcup"
        rcup.write_text(
            f"#!{sys.executable}\n"
            "import json\n"
            "import os\n"
            "from pathlib import Path\n"
            "import sys\n"
            "arguments = sys.argv[1:]\n"
            "Path(os.environ['FAKE_RCUP_LOG']).write_text(\n"
            "    json.dumps({'arguments': arguments, 'environment': {\n"
            "        name: os.environ.get(name)\n"
            "        for name in ('DOTFILES_DIR', 'DOTFILES_PRIVATE_DIR', 'HOME', 'RCRC')\n"
            "    }}),\n"
            "    encoding='utf-8',\n"
            ")\n"
            "directory = Path(arguments[arguments.index('-d') + 1])\n"
            "home = Path(os.environ['HOME'])\n"
            "for source in arguments[arguments.index('-d') + 2:]:\n"
            "    target = home / ('.' + source)\n"
            "    target.parent.mkdir(parents=True, exist_ok=True)\n"
            "    if target.is_symlink():\n"
            "        target.unlink()\n"
            "    target.symlink_to(directory / source)\n",
            encoding="utf-8",
        )
        rcup.chmod(0o755)
        return manifest, rcup

    def test_link_retained_targets_scopes_rcm_to_manifest_deferred_public_sources(self) -> None:
        manifest, rcup = self._retained_fixture()
        rcup_log = self.root / "rcup.json"
        with mock.patch.dict(os.environ, {"FAKE_RCUP_LOG": str(rcup_log)}):
            completed = self._retained_command(manifest, rcup)

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout, "retained rcm links complete\ttargets=2\n")
        record = json.loads(rcup_log.read_text(encoding="utf-8"))
        self.assertEqual(
            record["arguments"],
            [
                "-K",
                "-d",
                str(self.public),
                "Brewfile",
                "config/mise/config.toml",
            ],
        )
        self.assertEqual(
            record["environment"],
            {
                "DOTFILES_DIR": str(self.public),
                "DOTFILES_PRIVATE_DIR": str(self.private),
                "HOME": str(self.home),
                "RCRC": str(self.public / "rcrc"),
            },
        )
        self.assertEqual(os.readlink(self.home / ".Brewfile"), str(self.public / "Brewfile"))
        self.assertEqual(
            os.readlink(self.home / ".config/mise/config.toml"),
            str(self.public / "config/mise/config.toml"),
        )
        self.assertFalse((self.home / ".zshrc").exists())

    def test_link_retained_targets_refuses_regular_and_foreign_targets_before_rcm(self) -> None:
        manifest, rcup = self._retained_fixture()
        rcup_log = self.root / "rcup.json"
        target = self.home / ".Brewfile"
        target.write_text("local override\n", encoding="utf-8")
        with mock.patch.dict(os.environ, {"FAKE_RCUP_LOG": str(rcup_log)}):
            regular = self._retained_command(manifest, rcup)
        self.assertEqual(regular.returncode, 2)
        self.assertIn("retained rcm target is not an owned symlink: .Brewfile", regular.stderr)
        self.assertFalse(rcup_log.exists())

        target.unlink()
        target.symlink_to(self.root / "foreign")
        with mock.patch.dict(os.environ, {"FAKE_RCUP_LOG": str(rcup_log)}):
            foreign = self._retained_command(manifest, rcup)
        self.assertEqual(foreign.returncode, 2)
        self.assertIn("retained rcm target is a foreign symlink: .Brewfile", foreign.stderr)
        self.assertFalse(rcup_log.exists())

    def test_link_retained_targets_uses_only_the_public_rcm_directory(self) -> None:
        manifest, _fake_rcup = self._retained_fixture()
        self._write(self.private, "Brewfile", "private fixture\n")
        rcup = shutil.which("rcup")
        self.assertIsNotNone(rcup, "rcup must be installed for the retained-link fixture")

        completed = self._command(
            "link-retained",
            "--public-targets",
            str(manifest),
            "--rcup",
            str(rcup),
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(os.readlink(self.home / ".Brewfile"), str(self.public / "Brewfile"))
        self.assertEqual(
            os.readlink(self.home / ".config/mise/config.toml"),
            str(self.public / "config/mise/config.toml"),
        )
        self.assertFalse((self.home / ".zshrc").exists())

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

    def test_cutover_backup_is_complete_private_and_exclusive(self) -> None:
        public_manifest, private_manifest = self._configure_cutover_fixture()
        backup = self.root / "cutover-backup.json"

        completed = self._cutover_backup(public_manifest, private_manifest, backup)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(backup.read_text(encoding="utf-8"))
        self.assertEqual(payload["schema"], 1)
        self.assertEqual(payload["approval_sha256"], self._plan_digest(payload))
        self.assertEqual(
            [link["target"] for link in payload["links"]],
            [".missing", ".zshrc", ".zshrc.local"],
        )
        self.assertEqual(payload["private"], str(self.private))
        self.assertEqual(backup.stat().st_mode & 0o777, 0o600)
        original = backup.read_bytes()

        verified = self._cutover_command(
            "cutover-backup-verify",
            public_manifest,
            private_manifest,
            "--backup",
            str(backup),
        )
        self.assertEqual(verified.returncode, 0, verified.stderr)
        self.assertIn("cutover backup verified\ttargets=3", verified.stdout)

        repeated = self._cutover_backup(public_manifest, private_manifest, backup)
        self.assertEqual(repeated.returncode, 2)
        self.assertIn("cutover backup already exists", repeated.stderr)
        self.assertEqual(backup.read_bytes(), original)

        symlink_target = self.root / "symlink-target.json"
        symlink_target.write_bytes(original)
        symlink_target.chmod(0o600)
        backup.unlink()
        backup.symlink_to(symlink_target)
        refused_symlink = self._cutover_command(
            "cutover-backup-verify",
            public_manifest,
            private_manifest,
            "--backup",
            str(backup),
        )
        self.assertEqual(refused_symlink.returncode, 2)
        self.assertIn("cannot inspect cutover backup", refused_symlink.stderr)

    def test_cutover_backup_rejects_portable_target_aliases(self) -> None:
        public_manifest, private_manifest = self._configure_cutover_fixture()
        with public_manifest.open("a", encoding="utf-8") as manifest:
            manifest.write("other\t.ZSHRC\tshadow\tdot_ZSHRC\tfile\n")

        completed = self._cutover_backup(
            public_manifest,
            private_manifest,
            self.root / "aliased-targets.json",
        )

        self.assertEqual(completed.returncode, 2)
        self.assertIn("portable cutover target alias .ZSHRC", completed.stderr)

    def test_cutover_backup_rejects_option_like_sources(self) -> None:
        public_manifest, private_manifest = self._configure_cutover_fixture()
        with public_manifest.open("a", encoding="utf-8") as manifest:
            manifest.write("-option\t.option\tshadow\tdot_option\tfile\n")

        completed = self._cutover_backup(
            public_manifest,
            private_manifest,
            self.root / "option-source.json",
        )

        self.assertEqual(completed.returncode, 2)
        self.assertIn("source must not look like an option: -option", completed.stderr)

    def test_cutover_backup_accepts_trailing_private_metadata(self) -> None:
        public_manifest, private_manifest = self._configure_cutover_fixture()
        lines = private_manifest.read_text(encoding="utf-8").splitlines()
        private_manifest.write_text(
            "\n".join(f"{line}\tfixture_metadata" for line in lines) + "\n",
            encoding="utf-8",
        )

        completed = self._cutover_backup(
            public_manifest,
            private_manifest,
            self.root / "private-metadata.json",
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_cutover_backup_rejects_reordered_private_ownership_columns(self) -> None:
        public_manifest, private_manifest = self._configure_cutover_fixture()
        content = private_manifest.read_text(encoding="utf-8")
        private_manifest.write_text(
            content.replace(
                "target_shape\tmode\tchezmoi_source",
                "target_shape\tchezmoi_source\tmode",
                1,
            ),
            encoding="utf-8",
        )

        completed = self._cutover_backup(
            public_manifest,
            private_manifest,
            self.root / "reordered-private.json",
        )

        self.assertEqual(completed.returncode, 2)
        self.assertIn(
            "private chezmoi target manifest header must start with",
            completed.stderr,
        )

    def test_cutover_commands_derive_manifests_from_effective_repositories(self) -> None:
        public_override = self.root / "public-override"
        private_override = self.root / "private-override"

        args = RCM_LINKS.parse_args(
            (
                "cutover-backup",
                "--public-dir",
                str(public_override),
                "--private-dir",
                str(private_override),
                "--output",
                str(self.root / "backup.json"),
            )
        )

        self.assertEqual(
            args.public_targets,
            public_override / "docs/chezmoi-targets.tsv",
        )
        self.assertEqual(
            args.private_targets,
            private_override / "docs/chezmoi-private-targets.tsv",
        )

    def test_cutover_backup_rejects_invalid_existing_private_paths(self) -> None:
        zshrc = self._write(self.public, "zshrc", "public zshrc\n")
        self._commit(self.public, "add public-only invalid-private fixture")
        public_manifest = self.root / "public-invalid-private.tsv"
        public_manifest.write_text(
            "rcm_source\ttarget\tdisposition\tchezmoi_source\tmode\n"
            "zshrc\t.zshrc\tshadow\tdot_zshrc\tfile\n",
            encoding="utf-8",
        )
        self._write_fake_lsrc(((".zshrc", zshrc),))
        self._link(".zshrc", zshrc)

        regular_file = self.root / "private-regular-file"
        regular_file.write_text("not a checkout\n", encoding="utf-8")
        broken_symlink = self.root / "private-broken-link"
        broken_symlink.symlink_to(self.root / "missing-private-target")
        for private_path, expected in (
            (regular_file, "private dotfiles repository is not a directory"),
            (broken_symlink, "cannot resolve private dotfiles repository"),
        ):
            with self.subTest(private_path=private_path.name):
                completed = self._cutover_command(
                    "cutover-backup",
                    public_manifest,
                    private_path / "docs/chezmoi-private-targets.tsv",
                    "--output",
                    str(self.root / f"{private_path.name}.json"),
                    private_dir=private_path,
                )
                self.assertEqual(completed.returncode, 2)
                self.assertIn(expected, completed.stderr)

    def test_cutover_backup_rechecks_the_complete_snapshot(self) -> None:
        first_link = RCM_LINKS.CutoverLink(
            "public",
            PurePosixPath("zshrc"),
            PurePosixPath(".zshrc"),
            "/fixture/public/zshrc",
        )
        second_link = RCM_LINKS.CutoverLink(
            "public",
            PurePosixPath("zshrc"),
            PurePosixPath(".zshrc"),
            "/other/public/zshrc",
        )
        initial_map = {PurePosixPath(".zshrc"): Path("/fixture/public/zshrc")}

        with self.assertRaisesRegex(
            RCM_LINKS.InventoryError,
            "HOME links changed while the cutover backup was captured",
        ):
            RCM_LINKS.require_stable_cutover_snapshot(
                initial_map,
                dict(initial_map),
                (first_link,),
                (second_link,),
            )

        with self.assertRaisesRegex(
            RCM_LINKS.InventoryError,
            "live rcm map changed while the cutover backup was captured",
        ):
            RCM_LINKS.require_stable_cutover_snapshot(
                initial_map,
                {PurePosixPath(".other"): Path("/fixture/public/other")},
                (first_link,),
                (first_link,),
            )

    def test_cutover_backup_survives_directory_sync_failure(self) -> None:
        destination = self.root / "sync-failure.json"
        payload = {"schema": 1, "fixture": "durable publication boundary"}

        with mock.patch.object(
            RCM_LINKS.os,
            "fsync",
            side_effect=(None, OSError("fixture directory sync failure")),
        ):
            with self.assertRaisesRegex(
                RCM_LINKS.InventoryError,
                "cutover backup was published at",
            ):
                RCM_LINKS.write_exclusive_cutover_backup(destination, payload)

        self.assertEqual(destination.stat().st_mode & 0o777, 0o600)
        self.assertEqual(
            json.loads(destination.read_text(encoding="utf-8")),
            payload,
        )
        self.assertEqual(list(self.root.glob(".sync-failure.json.staged-*")), [])

    def test_cutover_backup_supports_an_absent_private_checkout(self) -> None:
        zshrc = self._write(self.public, "zshrc", "public zshrc\n")
        (self.public / "rcrc").write_text(
            'DOTFILES_DIRS="${DOTFILES_DIR} ${DOTFILES_PRIVATE_DIR}"\n',
            encoding="utf-8",
        )
        self._commit(self.public, "add public-only cutover fixture")
        public_manifest = self.root / "public-only-targets.tsv"
        public_manifest.write_text(
            "rcm_source\ttarget\tdisposition\tchezmoi_source\tmode\n"
            "zshrc\t.zshrc\tshadow\tdot_zshrc\tfile\n",
            encoding="utf-8",
        )
        absent_private = self.root / "private-absent"
        self._write_fake_lsrc(((".zshrc", zshrc),))
        self._link(".zshrc", zshrc)
        backup = self.root / "public-only.json"

        completed = self._cutover_command(
            "cutover-backup",
            public_manifest,
            absent_private / "docs/chezmoi-private-targets.tsv",
            "--output",
            str(backup),
            private_dir=absent_private,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(backup.read_text(encoding="utf-8"))
        self.assertIsNone(payload["private"])
        self.assertEqual([link["target"] for link in payload["links"]], [".zshrc"])

        fallback = self.public.parent / "dotfiles-private-absent"
        fallback.mkdir()
        (self.home / ".zshrc").unlink()
        (self.home / ".zshrc").write_text("rendered zshrc\n", encoding="utf-8")
        rcup = shutil.which("rcup")
        self.assertIsNotNone(rcup, "rcup must be installed for public-only restore")
        asserting_rcup = self.root / "asserting-rcup"
        asserting_rcup.write_text(
            f"#!{sys.executable}\n"
            "import os\n"
            "import sys\n"
            f"expected = {str(absent_private)!r}\n"
            "if os.environ.get('DOTFILES_PRIVATE_DIR') != expected:\n"
            "    raise SystemExit('wrong private repository path')\n"
            f"os.execv({str(rcup)!r}, [{str(rcup)!r}, *sys.argv[1:]])\n",
            encoding="utf-8",
        )
        asserting_rcup.chmod(0o755)

        restored = self._cutover_command(
            "cutover-restore",
            public_manifest,
            absent_private / "docs/chezmoi-private-targets.tsv",
            "--backup",
            str(backup),
            "--confirm",
            payload["approval_sha256"],
            "--rcup",
            str(asserting_rcup),
            private_dir=absent_private,
        )

        self.assertEqual(restored.returncode, 0, restored.stderr)
        self.assertEqual(os.readlink(self.home / ".zshrc"), str(zshrc))

    def test_public_only_restore_refuses_a_private_checkout_that_appears(self) -> None:
        private_dir = self.root / "appeared-private"
        private_dir.mkdir()
        backup = RCM_LINKS.CutoverBackup(
            self.home,
            self.public,
            None,
            (
                RCM_LINKS.CutoverLink(
                    "public",
                    PurePosixPath("zshrc"),
                    PurePosixPath(".zshrc"),
                    str(self.public / "zshrc"),
                ),
            ),
            "0" * 64,
        )

        with self.assertRaisesRegex(
            RCM_LINKS.InventoryError,
            "private repository appeared after public-only backup validation",
        ):
            RCM_LINKS.restore_cutover_backup(
                backup,
                rcup="must-not-run",
                private_dir=private_dir,
            )

    def test_cutover_backup_rejects_manifest_and_live_map_drift(self) -> None:
        public_manifest, private_manifest = self._configure_cutover_fixture()
        extra = self._write(self.public, "extra", "unmanifested\n")
        self._write_fake_lsrc(
            (
                (".extra", extra),
                (".missing", self.public / "missing"),
                (".zshrc", self.public / "zshrc"),
                (".zshrc.local", self.private / "zshrc.local"),
            )
        )

        completed = self._cutover_backup(
            public_manifest,
            private_manifest,
            self.root / "drifted.json",
        )
        self.assertEqual(completed.returncode, 2)
        self.assertIn("unmanifested targets: .extra", completed.stderr)
        self.assertFalse((self.root / "drifted.json").exists())

    def test_cutover_backup_rejects_non_exact_live_link(self) -> None:
        public_manifest, private_manifest = self._configure_cutover_fixture()
        (self.home / ".zshrc").unlink()
        (self.home / ".zshrc").symlink_to("../public/zshrc")

        completed = self._cutover_backup(
            public_manifest,
            private_manifest,
            self.root / "relative.json",
        )
        self.assertEqual(completed.returncode, 2)
        self.assertIn("not the exact absolute rcm link: .zshrc", completed.stderr)

    def test_cutover_restore_uses_rcm_and_verifies_every_link(self) -> None:
        public_manifest, private_manifest = self._configure_cutover_fixture()
        backup = self.root / "cutover-backup.json"
        created = self._cutover_backup(public_manifest, private_manifest, backup)
        self.assertEqual(created.returncode, 0, created.stderr)
        payload = json.loads(backup.read_text(encoding="utf-8"))
        for target in (".missing", ".zshrc", ".zshrc.local"):
            path = self.home / target
            path.unlink()
            path.write_text(f"rendered {target}\n", encoding="utf-8")
        rcup = shutil.which("rcup")
        self.assertIsNotNone(rcup, "rcup must be installed for the cutover restore fixture")

        restored = self._cutover_command(
            "cutover-restore",
            public_manifest,
            private_manifest,
            "--backup",
            str(backup),
            "--confirm",
            payload["approval_sha256"],
            "--rcup",
            str(rcup),
        )
        self.assertEqual(restored.returncode, 0, restored.stderr)
        self.assertIn("cutover restore complete\ttargets=3", restored.stdout)
        for link in payload["links"]:
            self.assertTrue((self.home / link["target"]).is_symlink())
            self.assertEqual(os.readlink(self.home / link["target"]), link["link_target"])

    def test_cutover_restore_rejects_tampering_and_foreign_links_before_rcm(self) -> None:
        public_manifest, private_manifest = self._configure_cutover_fixture()
        backup = self.root / "cutover-backup.json"
        created = self._cutover_backup(public_manifest, private_manifest, backup)
        self.assertEqual(created.returncode, 0, created.stderr)
        payload = json.loads(backup.read_text(encoding="utf-8"))
        digest = payload["approval_sha256"]
        payload["approval_sha256"] = ("0" if digest[0] != "0" else "1") + digest[1:]
        backup.write_text(json.dumps(payload), encoding="utf-8")
        backup.chmod(0o600)

        tampered = self._cutover_command(
            "cutover-restore",
            public_manifest,
            private_manifest,
            "--backup",
            str(backup),
            "--confirm",
            payload["approval_sha256"],
        )
        self.assertEqual(tampered.returncode, 2)
        self.assertIn("content does not match its approval_sha256", tampered.stderr)

        payload["approval_sha256"] = self._plan_digest(payload)
        backup.write_text(json.dumps(payload), encoding="utf-8")
        backup.chmod(0o600)
        foreign = self.home / ".zshrc"
        foreign.unlink()
        foreign.symlink_to(self.root / "foreign")
        refused = self._cutover_command(
            "cutover-restore",
            public_manifest,
            private_manifest,
            "--backup",
            str(backup),
            "--confirm",
            payload["approval_sha256"],
        )
        self.assertEqual(refused.returncode, 2)
        self.assertIn("foreign symlink: .zshrc", refused.stderr)
        self.assertEqual(os.readlink(foreign), str(self.root / "foreign"))

    def test_cutover_backup_rejects_wrong_repository_value_kind(self) -> None:
        public_manifest, private_manifest = self._configure_cutover_fixture()
        backup = self.root / "wrong-repository-kind.json"
        created = self._cutover_backup(public_manifest, private_manifest, backup)
        self.assertEqual(created.returncode, 0, created.stderr)
        payload = json.loads(backup.read_text(encoding="utf-8"))
        payload["links"][0]["repository"] = []
        payload["approval_sha256"] = self._plan_digest(payload)
        backup.write_text(json.dumps(payload), encoding="utf-8")
        backup.chmod(0o600)

        refused = self._cutover_command(
            "cutover-backup-verify",
            public_manifest,
            private_manifest,
            "--backup",
            str(backup),
        )

        self.assertEqual(refused.returncode, 2)
        self.assertIn("cutover backup link 0 fields are invalid", refused.stderr)
        self.assertNotIn("Traceback", refused.stderr)

    def test_cutover_restore_backup_survives_partial_rcup_and_retry(self) -> None:
        public_manifest, private_manifest = self._configure_cutover_fixture()
        backup = self.root / "cutover-backup.json"
        created = self._cutover_backup(public_manifest, private_manifest, backup)
        self.assertEqual(created.returncode, 0, created.stderr)
        payload = json.loads(backup.read_text(encoding="utf-8"))
        for target in (".missing", ".zshrc", ".zshrc.local"):
            path = self.home / target
            path.unlink()
            path.write_text(f"rendered {target}\n", encoding="utf-8")
        original_backup = backup.read_bytes()
        partial_rcup = self.root / "partial-rcup"
        partial_rcup.write_text(
            f"#!{sys.executable}\n"
            "import os\n"
            "from pathlib import Path\n"
            "home = Path(os.environ['HOME'])\n"
            "target = home / '.missing'\n"
            "target.unlink()\n"
            "target.symlink_to(Path(os.environ['DOTFILES_DIR']) / 'missing')\n"
            "raise SystemExit(7)\n",
            encoding="utf-8",
        )
        partial_rcup.chmod(0o755)

        partial = self._cutover_command(
            "cutover-restore",
            public_manifest,
            private_manifest,
            "--backup",
            str(backup),
            "--confirm",
            payload["approval_sha256"],
            "--rcup",
            str(partial_rcup),
        )
        self.assertEqual(partial.returncode, 2)
        self.assertIn("command failed (7)", partial.stderr)
        self.assertEqual(backup.read_bytes(), original_backup)
        self.assertTrue((self.home / ".missing").is_symlink())
        self.assertFalse((self.home / ".zshrc").is_symlink())

        rcup = shutil.which("rcup")
        self.assertIsNotNone(rcup, "rcup must be installed for the cutover retry fixture")
        retried = self._cutover_command(
            "cutover-restore",
            public_manifest,
            private_manifest,
            "--backup",
            str(backup),
            "--confirm",
            payload["approval_sha256"],
            "--rcup",
            str(rcup),
        )
        self.assertEqual(retried.returncode, 0, retried.stderr)
        self.assertEqual(backup.read_bytes(), original_backup)

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

    def test_inventory_discovers_untracked_current_top_level(self) -> None:
        self._write(self.public, "zshrc")
        self._write(self.public, "missing")
        self._commit(self.public, "add public sources")
        untracked = self._write(self.public, "new-root/excluded")
        self._write(self.private, "codex/hooks.json", "{}\n")
        self._commit(self.private, "add exact dedicated source")
        self._link(".new-root/excluded", untracked)

        completed = self._inventory()
        self.assertEqual(completed.returncode, 0, completed.stderr)
        records = {record["target"]: record for record in json.loads(completed.stdout)["records"]}
        self.assertEqual(
            (records[".new-root/excluded"]["disposition"], records[".new-root/excluded"]["status"]),
            ("obsolete", "linked"),
        )

    def test_inventory_normalizes_case_aliases_to_stored_home_spelling(self) -> None:
        self._write(self.public, "Justfile")
        private_justfile = self._write(self.private, "justfile")
        self._write(self.private, "codex/hooks.json", "{}\n")
        self._commit(self.public, "add case-colliding public source")
        self._commit(self.private, "add current private source")
        self._link(".justfile", private_justfile)

        original_walk_links = RCM_LINKS.walk_links

        def walk_links_with_case_alias(root: Path) -> set[Path]:
            links = original_walk_links(root)
            if root == self.home / ".Justfile":
                links.add(root)
            return links

        def stored_spelling(home: Path, path: Path) -> PurePosixPath:
            if path == home / ".Justfile":
                return PurePosixPath(".justfile")
            return RCM_LINKS.actual_home_relative(home, path)

        with mock.patch.object(RCM_LINKS, "walk_links", side_effect=walk_links_with_case_alias):
            inventory_records = RCM_LINKS.inventory(
                home=self.home,
                public=self.public,
                private=self.private,
                patterns=RCM_LINKS.load_owner_patterns(self.owners),
                rcm_map={PurePosixPath(".justfile"): private_justfile},
                spelling_resolver=stored_spelling,
            )
        records = {record.target: record for record in inventory_records}
        self.assertNotIn(".Justfile", records)
        self.assertEqual(
            (records[".justfile"].disposition, records[".justfile"].status),
            ("rcm", "linked"),
        )

    def test_inventory_normalizes_inverse_expected_case_alias_and_rejects_overlap(self) -> None:
        self._write(self.public, "Justfile")
        private_justfile = self._write(self.private, "justfile")
        self._write(self.private, "codex/hooks.json", "{}\n")
        self._commit(self.public, "add historical public spelling")
        self._commit(self.private, "add current private source")
        self._link(".justfile", private_justfile)
        patterns = RCM_LINKS.load_owner_patterns(self.owners)

        def stored_spelling(_home: Path, _path: Path) -> PurePosixPath:
            return PurePosixPath(".justfile")

        def stored_expected(_home: Path, _target: PurePosixPath) -> PurePosixPath:
            if _target in {PurePosixPath(".Justfile"), PurePosixPath(".justfile")}:
                return PurePosixPath(".justfile")
            return _target

        records = RCM_LINKS.inventory(
            home=self.home,
            public=self.public,
            private=self.private,
            patterns=patterns,
            rcm_map={PurePosixPath(".Justfile"): private_justfile},
            spelling_resolver=stored_spelling,
            expected_spelling_resolver=stored_expected,
        )
        by_target = {record.target: record for record in records}
        self.assertEqual(set(by_target) & {".Justfile", ".justfile"}, {".justfile"})
        self.assertEqual(
            (by_target[".justfile"].disposition, by_target[".justfile"].status),
            ("rcm", "linked"),
        )

        with self.assertRaisesRegex(
            RCM_LINKS.InventoryError,
            "expected ownership aliases overlap",
        ):
            RCM_LINKS.inventory(
                home=self.home,
                public=self.public,
                private=self.private,
                patterns=patterns,
                rcm_map={
                    PurePosixPath(".Justfile"): private_justfile,
                    PurePosixPath(".justfile"): private_justfile,
                },
                spelling_resolver=stored_spelling,
                expected_spelling_resolver=stored_expected,
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
