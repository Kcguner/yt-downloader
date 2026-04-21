import unittest
from pathlib import Path
from unittest import mock

import gui_history


class TestGuiHistory(unittest.TestCase):
    def test_append_and_has_url(self):
        path = Path("test/tmp-history.json")
        try:
            with mock.patch("gui_history.history_path", return_value=path):
                gui_history.append_history({"url": "https://example.com/a", "title": "A"})
                self.assertTrue(gui_history.has_url("https://example.com/a"))
                self.assertFalse(gui_history.has_url("https://example.com/b"))
                data = gui_history.load_history()
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]["title"], "A")
        finally:
            if path.exists():
                path.unlink()

    def test_load_history_handles_invalid_json(self):
        path = Path("test/tmp-history-invalid.json")
        try:
            path.write_text("{invalid", encoding="utf-8")
            with mock.patch("gui_history.history_path", return_value=path):
                data = gui_history.load_history()
            self.assertEqual(data, [])
        finally:
            if path.exists():
                path.unlink()

    def test_recent_history_and_clear_history(self):
        path = Path("test/tmp-history-recent.json")
        try:
            with mock.patch("gui_history.history_path", return_value=path):
                for idx in range(60):
                    gui_history.append_history({"url": f"https://example.com/{idx}"})
                recent = gui_history.recent_history(50)
                self.assertEqual(len(recent), 50)
                self.assertEqual(recent[0]["url"], "https://example.com/59")
                self.assertEqual(recent[-1]["url"], "https://example.com/10")
                gui_history.clear_history()
                self.assertEqual(gui_history.load_history(), [])
        finally:
            if path.exists():
                path.unlink()


if __name__ == "__main__":
    unittest.main()
