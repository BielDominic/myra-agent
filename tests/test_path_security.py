import tempfile
import unittest
from pathlib import Path

from tasks.path_security import path_within_workspace


class WorkspaceContainmentTests(unittest.TestCase):
    def test_accepts_workspace_root_and_child(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "workspace"
            root.mkdir()
            child = root / "nested" / "file.txt"
            self.assertTrue(path_within_workspace(str(root), str(root)))
            self.assertTrue(path_within_workspace(str(child), str(root)))

    def test_rejects_parent_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "workspace"
            root.mkdir()
            outside = Path(tmp) / "outside.txt"
            self.assertFalse(path_within_workspace(str(outside), str(root)))
            self.assertFalse(path_within_workspace(str(root / ".." / "outside.txt"), str(root)))

    def test_rejects_sibling_with_shared_string_prefix(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "workspace"
            sibling = Path(tmp) / "workspace-escape"
            root.mkdir()
            sibling.mkdir()
            self.assertFalse(path_within_workspace(str(sibling / "secret.txt"), str(root)))


if __name__ == "__main__":
    unittest.main()
