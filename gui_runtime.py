from __future__ import annotations

import os
import re
import shutil
import socket
import sys
import json
from pathlib import Path
from urllib import error, request

FFMPEG_DOWNLOAD_URL = 'https://ffmpeg.org/download.html'

_URL_RE = re.compile(r'^https?://\S+$', flags=re.IGNORECASE)


def is_valid_download_url(url: str) -> bool:
    return bool(_URL_RE.match((url or '').strip()))


def has_internet_connection(timeout: float = 1.5) -> bool:
    try:
        with socket.create_connection(('1.1.1.1', 53), timeout=timeout):
            return True
    except OSError:
        return False


def _runtime_root() -> Path:
    meipass = getattr(sys, '_MEIPASS', None)
    if meipass:
        return Path(meipass)
    return Path(__file__).resolve().parent


def _bundled_ffmpeg_dir(root: Path) -> str | None:
    ffmpeg_dir = root / 'ffmpeg-bin'
    candidates = ('ffmpeg.exe', 'ffmpeg') if os.name == 'nt' else ('ffmpeg', 'ffmpeg.exe')
    for name in candidates:
        if (ffmpeg_dir / name).is_file():
            return str(ffmpeg_dir)
    return None


def resolve_ffmpeg_location() -> tuple[str | None, str]:
    bundled = _bundled_ffmpeg_dir(_runtime_root())
    if bundled:
        return bundled, 'bundled'

    system_ffmpeg = shutil.which('ffmpeg')
    if system_ffmpeg:
        return system_ffmpeg, 'system'

    return None, 'missing'


def map_download_exception_key(exc: BaseException) -> str:
    from yt_dlp.utils import DownloadError, ExtractorError, PostProcessingError

    if isinstance(exc, ExtractorError):
        return 'error.extractor'
    if isinstance(exc, PostProcessingError):
        return 'error.postprocess'
    if isinstance(exc, DownloadError):
        return 'error.download'
    return 'error.unexpected'


def _version_parts(value: str | None) -> tuple[int, ...]:
    numbers = re.findall(r'\d+', value or '')
    if not numbers:
        return (0,)
    return tuple(int(part) for part in numbers)


def is_newer_version(candidate: str | None, current: str | None) -> bool:
    return _version_parts(candidate) > _version_parts(current)


def fetch_json(url: str, timeout: float = 3.0, headers: dict[str, str] | None = None) -> dict | None:
    req = request.Request(
        url,
        headers=headers or {'User-Agent': 'yt-downloader-gui/3.1'},
    )
    try:
        with request.urlopen(req, timeout=timeout) as response:
            payload = response.read().decode('utf-8', errors='ignore')
    except (error.URLError, OSError, TimeoutError):
        return None

    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return None

    if isinstance(data, dict):
        return data
    return None


def fetch_latest_ytdlp_version(timeout: float = 3.0) -> str | None:
    data = fetch_json('https://pypi.org/pypi/yt-dlp/json', timeout=timeout)
    if not data:
        return None
    version = data.get('info', {}).get('version')
    if isinstance(version, str) and version.strip():
        return version.strip()
    return None


def fetch_latest_release(repo: str, timeout: float = 3.0) -> tuple[str | None, str | None]:
    data = fetch_json(
        f'https://api.github.com/repos/{repo}/releases/latest',
        timeout=timeout,
        headers={
            'Accept': 'application/vnd.github+json',
            'User-Agent': 'yt-downloader-gui/3.1',
        },
    )
    if not data:
        return None, None

    tag = data.get('tag_name')
    url = data.get('html_url')
    if not isinstance(tag, str) or not tag.strip():
        tag = None
    if not isinstance(url, str) or not url.strip():
        url = None
    return tag, url
