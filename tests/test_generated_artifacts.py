import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import rag


class GeneratedArtifactTests(unittest.TestCase):
    def test_project_files_are_packaged_with_relative_paths(self):
        answer = """\
```file path=public/index.php
<?php
echo "Hello";
```
```file path=README.md
# Example project
```
"""

        with tempfile.TemporaryDirectory() as temporary_dir:
            with patch.object(rag, "PROJECT_DIR", Path(temporary_dir)):
                archive_path = rag.save_generated_php_code(answer)

            self.assertTrue(archive_path.endswith(".zip"))
            with zipfile.ZipFile(archive_path) as archive:
                self.assertEqual(
                    set(archive.namelist()),
                    {"public/index.php", "README.md"},
                )
                self.assertIn(
                    b'echo "Hello";',
                    archive.read("public/index.php"),
                )

    def test_single_php_code_block_remains_downloadable(self):
        answer = """\
```php
<?php
echo "Hello";
```
"""

        with tempfile.TemporaryDirectory() as temporary_dir:
            with patch.object(rag, "PROJECT_DIR", Path(temporary_dir)):
                file_path = rag.save_generated_php_code(answer)

            self.assertEqual(Path(file_path).name, "generated_solution.php")
            self.assertIn('echo "Hello";', Path(file_path).read_text(encoding="utf-8"))

    def test_project_archive_rejects_paths_outside_project(self):
        answer = """\
```file path=../outside.php
<?php echo "unsafe";
```
"""

        with tempfile.TemporaryDirectory() as temporary_dir:
            with patch.object(rag, "PROJECT_DIR", Path(temporary_dir)):
                with self.assertRaisesRegex(ValueError, "unsafe file path"):
                    rag.save_generated_php_code(answer)


if __name__ == "__main__":
    unittest.main()
