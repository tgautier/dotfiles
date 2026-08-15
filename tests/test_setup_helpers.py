from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile
import textwrap
import unittest


REPOSITORY = Path(__file__).resolve().parents[1]


class SetupHelperTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.home = self.root / "home"
        self.fake_bin = self.root / "bin"
        self.library = self.root / "libsqlite3.so.0"
        self.target = self.home / ".local/lib/flutter-ffi/libsqlite3.so"
        self.home.mkdir()
        self.fake_bin.mkdir()
        self.library.write_bytes(b"sqlite fixture\n")
        ldconfig = self.fake_bin / "ldconfig"
        ldconfig.write_text(
            textwrap.dedent(
                f"""\
                #!/bin/sh
                printf '%s\\n' 'libsqlite3.so.0 (libc6) => {self.library}'
                """
            ),
            encoding="utf-8",
        )
        ldconfig.chmod(0o700)
        self.environment = {
            key: value
            for key, value in os.environ.items()
            if key not in {"BASH_ENV", "ENV", "ZDOTDIR"}
        }
        self.environment.update(
            {
                "HOME": str(self.home),
                "PATH": f"{self.fake_bin}{os.pathsep}{self.environment['PATH']}",
                "ZDOTDIR": str(self.root / "zdotdir"),
            }
        )

    def run_helper(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["just", "_link-libsqlite3"],
            cwd=REPOSITORY,
            env=self.environment,
            check=False,
            capture_output=True,
            text=True,
        )

    def test_exact_link_is_created_once_without_second_run_mutation(self) -> None:
        first = self.run_helper()
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertTrue(self.target.is_symlink())
        self.assertEqual(os.readlink(self.target), str(self.library))
        first_metadata = self.target.lstat()

        second = self.run_helper()
        self.assertEqual(second.returncode, 0, second.stderr)
        second_metadata = self.target.lstat()
        self.assertEqual(second_metadata.st_ino, first_metadata.st_ino)
        self.assertEqual(second_metadata.st_mtime_ns, first_metadata.st_mtime_ns)

    def test_foreign_symlink_is_refused_and_preserved(self) -> None:
        self.target.parent.mkdir(parents=True)
        foreign = self.root / "foreign"
        foreign.write_bytes(b"foreign fixture\n")
        self.target.symlink_to(foreign)

        completed = self.run_helper()

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("refusing to replace foreign symlink", completed.stderr)
        self.assertEqual(os.readlink(self.target), str(foreign))

    def test_regular_file_is_refused_and_preserved(self) -> None:
        self.target.parent.mkdir(parents=True)
        self.target.write_bytes(b"regular fixture\n")

        completed = self.run_helper()

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("refusing to replace non-symlink target", completed.stderr)
        self.assertEqual(self.target.read_bytes(), b"regular fixture\n")


if __name__ == "__main__":
    unittest.main()
