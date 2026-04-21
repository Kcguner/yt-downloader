import unittest
from unittest import mock

import gui


def _has_ancestor(widget, ancestor):
    current = widget
    while current is not None:
        if current == ancestor:
            return True
        current = getattr(current, "master", None)
    return False


class TestGuiLayout(unittest.TestCase):
    def test_resolve_theme_palette_has_light_surface_tokens(self):
        palette = gui.resolve_theme_palette("light")

        self.assertEqual(palette["window_bg"], "#f4efe7")
        self.assertEqual(palette["card_bg"], "#fffaf2")
        self.assertEqual(palette["text_primary"], "#201815")
        self.assertNotEqual(palette["window_bg"], gui.resolve_theme_palette("dark")["window_bg"])

    def test_theme_and_language_controls_live_in_header_toolbar(self):
        with (
            mock.patch.object(gui, "load_config", return_value={"theme": "dark", "language": "en"}),
            mock.patch.object(gui, "save_config"),
        ):
            app = gui.App()

        try:
            self.assertTrue(hasattr(app, "_header_pref_bar"))
            self.assertTrue(hasattr(app, "_theme_menu"))
            self.assertTrue(hasattr(app, "_lang_menu"))
            self.assertFalse(_has_ancestor(app._theme_menu, app._settings_card))
            self.assertFalse(_has_ancestor(app._lang_menu, app._settings_card))
            self.assertTrue(_has_ancestor(app._theme_menu, app._header_pref_bar))
            self.assertTrue(_has_ancestor(app._lang_menu, app._header_pref_bar))
        finally:
            app.destroy()

    def test_switching_to_light_theme_updates_window_palette(self):
        with mock.patch.object(gui, "load_config", return_value={"theme": "dark", "language": "en"}):
            app = gui.App()

        try:
            with mock.patch.object(gui, "save_config"):
                app._set_theme(app._tr("theme.light"))
            self.assertEqual(app._theme, "light")
            self.assertEqual(app._palette["window_bg"], "#f4efe7")
            self.assertEqual(app.cget("fg_color"), "#f4efe7")
        finally:
            app.destroy()


if __name__ == "__main__":
    unittest.main()
