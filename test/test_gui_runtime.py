import unittest
from pathlib import Path
from unittest import mock

from yt_dlp.utils import DownloadError, ExtractorError, PostProcessingError

import gui_runtime


class TestGuiRuntime(unittest.TestCase):
    def test_is_valid_download_url(self):
        self.assertTrue(gui_runtime.is_valid_download_url("https://youtube.com/watch?v=abc"))
        self.assertTrue(gui_runtime.is_valid_download_url("http://example.com/video"))
        self.assertFalse(gui_runtime.is_valid_download_url("youtube.com/watch?v=abc"))
        self.assertFalse(gui_runtime.is_valid_download_url("not a url"))

    def test_map_download_exception(self):
        self.assertEqual(
            gui_runtime.map_download_exception_key(DownloadError("x")),
            "error.download",
        )
        self.assertEqual(
            gui_runtime.map_download_exception_key(ExtractorError("x")),
            "error.extractor",
        )
        self.assertEqual(
            gui_runtime.map_download_exception_key(PostProcessingError("x")),
            "error.postprocess",
        )
        self.assertEqual(
            gui_runtime.map_download_exception_key(RuntimeError("x")),
            "error.unexpected",
        )

    def test_resolve_ffmpeg_location_prefers_bundled(self):
        with (
            mock.patch("gui_runtime._runtime_root", return_value=Path("X:/runtime")),
            mock.patch("gui_runtime._bundled_ffmpeg_dir", return_value="X:/runtime/ffmpeg-bin"),
            mock.patch("gui_runtime.shutil.which", return_value="C:/ffmpeg/ffmpeg.exe"),
        ):
            location, source = gui_runtime.resolve_ffmpeg_location()

        self.assertEqual(location, "X:/runtime/ffmpeg-bin")
        self.assertEqual(source, "bundled")

    def test_resolve_ffmpeg_location_system_fallback(self):
        with (
            mock.patch("gui_runtime._runtime_root", return_value=Path("X:/missing")),
            mock.patch("gui_runtime.shutil.which", return_value="C:/ffmpeg/ffmpeg.exe"),
        ):
            location, source = gui_runtime.resolve_ffmpeg_location()

        self.assertEqual(location, "C:/ffmpeg/ffmpeg.exe")
        self.assertEqual(source, "system")

    def test_resolve_ffmpeg_location_missing(self):
        with (
            mock.patch("gui_runtime._runtime_root", return_value=Path("X:/missing")),
            mock.patch("gui_runtime.shutil.which", return_value=None),
        ):
            location, source = gui_runtime.resolve_ffmpeg_location()

        self.assertIsNone(location)
        self.assertEqual(source, "missing")


if __name__ == "__main__":
    unittest.main()
