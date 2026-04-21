import json
import unittest
from pathlib import Path
from unittest import mock

import gui_i18n


class TestGuiI18n(unittest.TestCase):
    def test_normalize_language(self):
        locales = {"tr": {}, "en": {}}
        self.assertEqual(gui_i18n.normalize_language("en", locales), "en")
        self.assertEqual(gui_i18n.normalize_language("de", locales), "tr")

    def test_translate_with_fallback(self):
        locales = {
            "tr": {"status.done": "Tamam"},
            "en": {},
        }
        self.assertEqual(gui_i18n.tr(locales, "en", "status.done"), "Tamam")
        self.assertEqual(gui_i18n.tr(locales, "en", "missing.key"), "missing.key")

    def test_save_and_load_config(self):
        cfg_path = Path("test/tmp-gui-config.json")
        try:
            with mock.patch("gui_i18n.config_path", return_value=cfg_path):
                gui_i18n.save_config({"language": "en"})
                data = gui_i18n.load_config()
            self.assertEqual(data["language"], "en")
        finally:
            if cfg_path.exists():
                cfg_path.unlink()

    def test_load_locales(self):
        base = Path("test/tmp-locales")
        base.mkdir(parents=True, exist_ok=True)
        (base / "tr.json").write_text(json.dumps({"a": "b"}), encoding="utf-8")
        (base / "en.json").write_text(json.dumps({"a": "c"}), encoding="utf-8")
        try:
            with mock.patch("gui_i18n.locales_dir", return_value=base):
                data = gui_i18n.load_locales()
            self.assertEqual(data["tr"]["a"], "b")
            self.assertEqual(data["en"]["a"], "c")
        finally:
            for p in base.glob("*.json"):
                p.unlink()
            base.rmdir()


if __name__ == "__main__":
    unittest.main()
