import unittest
from unittest import mock

import gui


def _has_ancestor(widget, ancestor):
    current = widget
    while current is not None:
        if current == ancestor:
            return True
        current = getattr(current, 'master', None)
    return False


class TestGuiLayout(unittest.TestCase):
    def test_resolve_theme_palette_has_light_surface_tokens(self):
        palette = gui.resolve_theme_palette('light')

        self.assertEqual(palette['window_bg'], '#f4efe7')
        self.assertEqual(palette['card_bg'], '#fffaf2')
        self.assertEqual(palette['text_primary'], '#201815')
        self.assertNotEqual(palette['window_bg'], gui.resolve_theme_palette('dark')['window_bg'])

    def test_theme_and_language_controls_live_in_header_toolbar(self):
        with (
            mock.patch.object(gui, 'load_config', return_value={'theme': 'dark', 'language': 'en'}),
            mock.patch.object(gui, 'save_config'),
        ):
            app = gui.App()

        try:
            self.assertTrue(hasattr(app, '_header_pref_bar'))
            self.assertTrue(hasattr(app, '_theme_menu'))
            self.assertTrue(hasattr(app, '_lang_menu'))
            self.assertFalse(_has_ancestor(app._theme_menu, app._settings_card))
            self.assertFalse(_has_ancestor(app._lang_menu, app._settings_card))
            self.assertTrue(_has_ancestor(app._theme_menu, app._header_pref_bar))
            self.assertTrue(_has_ancestor(app._lang_menu, app._header_pref_bar))
        finally:
            app.destroy()

    def test_switching_to_light_theme_updates_window_palette(self):
        with mock.patch.object(gui, 'load_config', return_value={'theme': 'dark', 'language': 'en'}):
            app = gui.App()

        try:
            with mock.patch.object(gui, 'save_config'):
                app._set_theme(app._tr('theme.light'))
            self.assertEqual(app._theme, 'light')
            self.assertEqual(app._palette['window_bg'], '#f4efe7')
            self.assertEqual(app.cget('fg_color'), '#f4efe7')
        finally:
            app.destroy()


class _Var:
    def __init__(self, value):
        self._value = value

    def get(self):
        return self._value


class TestGuiDownloadOptions(unittest.TestCase):
    def _make_app_stub(self):
        app = object.__new__(gui.App)
        tr_map = {
            'opt.best': 'En İyi',
            'opt.auto': 'Otomatik',
            'opt.unlimited': 'Sınırsız',
            'opt.hdr_sdr_only': 'Yalnız SDR',
            'opt.audio_best_vbr': 'En İyi (VBR)',
            'opt.channel_stereo': 'Stereo (2)',
            'opt.channel_mono': 'Mono (1)',
        }
        app._tr = lambda key, **_: tr_map.get(key, key)
        return app

    def test_build_video_opts(self):
        app = self._make_app_stub()
        app._res_var = _Var('1080p')
        app._vcodec_var = _Var('h264 (AVC)')
        app._fps_var = _Var('60')
        app._hdr_var = _Var('Yalnız SDR')

        opts = {}
        app._build_video_opts(opts, 'mp4')

        self.assertEqual(opts['merge_output_format'], 'mp4')
        self.assertIn('height<=1080', opts['format'])
        self.assertIn('[fps<=60]', opts['format'])
        self.assertIn('[vcodec^=avc]', opts['format'])
        self.assertIn('[dynamic_range!=HDR10]', opts['format'])

    def test_build_audio_opts(self):
        app = self._make_app_stub()
        app._abitrate_var = _Var('192k')
        app._samplerate_var = _Var('44100 Hz')
        app._channels_var = _Var('Stereo (2)')

        opts = {}
        app._build_audio_opts(opts, 'mp3')

        self.assertEqual(opts['format'], 'bestaudio/best')
        self.assertEqual(opts['postprocessors'][0]['preferredcodec'], 'mp3')
        self.assertEqual(opts['postprocessors'][0]['preferredquality'], '192')
        self.assertEqual(opts['postprocessor_args']['FFmpegExtractAudio'], ['-ar', '44100', '-ac', '2'])

    def test_default_output_template(self):
        self.assertEqual(
            gui.DEFAULT_OUTTMPL,
            '%(playlist_index|)s%(playlist_index& - |)s%(title)s.%(ext)s',
        )


if __name__ == '__main__':
    unittest.main()
