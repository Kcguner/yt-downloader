from __future__ import annotations

import os
import re
import shutil
import socket
import sys
from pathlib import Path

FFMPEG_DOWNLOAD_URL = "https://ffmpeg.org/download.html"

_URL_RE = re.compile(r"^https?://\S+$", flags=re.IGNORECASE)


def is_valid_download_url(url: str) -> bool:
    return bool(_URL_RE.match((url or "").strip()))


def has_internet_connection(timeout: float = 1.5) -> bool:
    try:
        with socket.create_connection(("1.1.1.1", 53), timeout=timeout):
            return True
    except OSError:
        return False


def _runtime_root() -> Path:
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass)
    return Path(__file__).resolve().parent


def _bundled_ffmpeg_dir(root: Path) -> str | None:
    ffmpeg_dir = root / "ffmpeg-bin"
    candidates = ("ffmpeg.exe", "ffmpeg") if os.name == "nt" else ("ffmpeg", "ffmpeg.exe")
    for name in candidates:
        if (ffmpeg_dir / name).is_file():
            return str(ffmpeg_dir)
    return None


def resolve_ffmpeg_location() -> tuple[str | None, str]:
    bundled = _bundled_ffmpeg_dir(_runtime_root())
    if bundled:
        return bundled, "bundled"

    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return system_ffmpeg, "system"

    return None, "missing"


def map_download_exception_key(exc: BaseException) -> str:
    from yt_dlp.utils import DownloadError, ExtractorError, PostProcessingError

    if isinstance(exc, ExtractorError):
        return "error.extractor"
    if isinstance(exc, PostProcessingError):
        return "error.postprocess"
    if isinstance(exc, DownloadError):
        return "error.download"
    return "error.unexpected"
