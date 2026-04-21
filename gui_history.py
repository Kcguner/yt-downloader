from __future__ import annotations

import json
from pathlib import Path


def history_path() -> Path:
    return Path.home() / '.yt-downloader' / 'history.json'


def load_history() -> list[dict]:
    path = history_path()
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return []
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    return []


def save_history(items: list[dict]) -> None:
    path = history_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding='utf-8')


def append_history(item: dict) -> None:
    items = load_history()
    items.append(item)
    save_history(items)


def has_url(url: str) -> bool:
    u = (url or '').strip()
    if not u:
        return False
    for item in load_history():
        if item.get('url') == u:
            return True
    return False


def recent_history(limit: int = 50) -> list[dict]:
    if limit <= 0:
        return []
    items = load_history()
    return list(reversed(items[-limit:]))


def clear_history() -> None:
    save_history([])
