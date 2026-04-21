from __future__ import annotations

import json
from pathlib import Path

DEFAULT_LANGUAGE = "tr"


def locales_dir() -> Path:
    return Path(__file__).resolve().parent / "locales"


def config_path() -> Path:
    return Path.home() / ".yt-downloader" / "config.json"


def load_locales() -> dict[str, dict[str, str]]:
    data: dict[str, dict[str, str]] = {}
    base_dir = locales_dir()
    for lang in ("tr", "en"):
        path = base_dir / f"{lang}.json"
        if not path.is_file():
            continue
        try:
            data[lang] = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
    return data


def load_config() -> dict:
    path = config_path()
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save_config(data: dict) -> None:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def normalize_language(lang: str | None, available: dict[str, dict[str, str]]) -> str:
    if lang and lang in available:
        return lang
    return DEFAULT_LANGUAGE if DEFAULT_LANGUAGE in available else (next(iter(available), DEFAULT_LANGUAGE))


def tr(locales: dict[str, dict[str, str]], lang: str, key: str, **kwargs) -> str:
    current = locales.get(lang, {})
    fallback = locales.get(DEFAULT_LANGUAGE, {})
    text = current.get(key, fallback.get(key, key))
    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            return text
    return text
