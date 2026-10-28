import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app


class AppStartupTests(unittest.TestCase):
    def setUp(self):
        app.ensure_vectorstore.clear()

    def tearDown(self):
        app.ensure_vectorstore.clear()

    def test_missing_vectorstore_is_built_on_startup(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            vectorstore_path = Path(temporary_dir) / "vectorstore"

            def build_index():
                vectorstore_path.mkdir()
                (vectorstore_path / "index.faiss").touch()
                (vectorstore_path / "index.pkl").touch()

            with (
                patch.object(app, "VECTORSTORE_PATH", vectorstore_path),
                patch.object(app, "build_vectorstore", side_effect=build_index) as build,
            ):
                app.ensure_vectorstore()

            build.assert_called_once()

    def test_existing_vectorstore_is_not_rebuilt(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            vectorstore_path = Path(temporary_dir)
            (vectorstore_path / "index.faiss").touch()
            (vectorstore_path / "index.pkl").touch()

            with (
                patch.object(app, "VECTORSTORE_PATH", vectorstore_path),
                patch.object(app, "build_vectorstore") as build,
            ):
                app.ensure_vectorstore()

            build.assert_not_called()

    def test_startup_reports_when_index_files_are_not_created(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            with (
                patch.object(app, "VECTORSTORE_PATH", Path(temporary_dir)),
                patch.object(app, "build_vectorstore"),
                self.assertRaisesRegex(FileNotFoundError, "index.faiss"),
            ):
                app.ensure_vectorstore()


if __name__ == "__main__":
    unittest.main()
