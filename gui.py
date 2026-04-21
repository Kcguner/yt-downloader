"""
YT Downloader — v3.1
Responsive dark UI with fullscreen support
"""

import customtkinter as ctk
import tkinter as tk
import threading
import os
import re
import queue
import subprocess
import sys
import webbrowser
from datetime import datetime
from tkinter import messagebox

from gui_history import append_history, clear_history, has_url, recent_history
from gui_i18n import load_config, load_locales, normalize_language, save_config, tr
from gui_runtime import (
    FFMPEG_DOWNLOAD_URL,
    fetch_latest_release,
    fetch_latest_ytdlp_version,
    has_internet_connection,
    is_newer_version,
    is_valid_download_url,
    map_download_exception_key,
    resolve_ffmpeg_location,
)

try:
    from tkinterdnd2 import DND_TEXT  # type: ignore
except ImportError:
    DND_TEXT = None

ctk.set_appearance_mode('dark')
ctk.set_default_color_theme('dark-blue')

__version__ = '3.1.0'
APP_RELEASE_REPO = 'Kcguner/yt-downloader'
DEFAULT_OUTTMPL = '%(playlist_index|)s%(playlist_index& - |)s%(title)s.%(ext)s'
WIDE_LAYOUT_MIN_WIDTH = 1280


def summarize_media_info(info: dict | None, fallback_url: str = '') -> dict[str, object]:
    info = info or {}
    is_playlist = info.get('_type') == 'playlist'
    if is_playlist:
        entries = [entry for entry in (info.get('entries') or []) if isinstance(entry, dict)]
        primary = entries[0] if entries else info
        count = info.get('playlist_count') or info.get('n_entries') or len(entries) or None
    else:
        primary = info
        count = None

    title = (
        primary.get('title')
        or info.get('title')
        or fallback_url
    )
    duration = primary.get('duration')
    channel = (
        primary.get('channel')
        or primary.get('uploader')
        or info.get('channel')
        or info.get('uploader')
        or '-'
    )

    return {
        'is_playlist': bool(is_playlist),
        'count': count,
        'title': title,
        'duration': duration,
        'channel': channel,
    }


def use_wide_layout(content_width: int) -> bool:
    return content_width >= WIDE_LAYOUT_MIN_WIDTH


def resolve_theme_palette(mode: str) -> dict[str, str]:
    mode = (mode or 'dark').lower()
    if mode == 'light':
        return {
            'window_bg': '#f4efe7',
            'card_bg': '#fffaf2',
            'card_edge': '#d9d1c6',
            'card_title': '#7b6659',
            'text_primary': '#201815',
            'text_secondary': '#5c4a3f',
            'text_muted': '#7d6a5e',
            'text_subtle': '#9d8b80',
            'title_accent': '#c83c2f',
            'title_text': '#201815',
            'dot': '#9d8b80',
            'input_bg': '#f2ebe2',
            'input_border': '#d6c9bb',
            'input_text': '#201815',
            'button_bg': '#e6ddd1',
            'button_hover': '#dacdbf',
            'button_text': '#2e2420',
            'danger': '#c83c2f',
            'danger_hover': '#e04a3d',
            'warning': '#a66a12',
            'warning_hover': '#bf7b17',
            'warning_text': '#fff5d6',
            'accent': '#b4583c',
            'accent_hover': '#c96a4d',
            'accent_soft': '#d78861',
            'accent_soft_hover': '#c67350',
            'accent_text': '#fff8f2',
            'success': '#2e8b57',
            'error': '#c83c2f',
            'progress_track': '#d7cec2',
            'info_bg': '#efe3d8',
            'info_edge': '#d2bcab',
            'warning_bg': '#f2ddb0',
            'warning_fg': '#6f4c00',
            'track_bg': '#f8f2ea',
            'track_badge_bg': '#ede3d8',
            'track_active_bg': '#f2e4d7',
            'track_active_edge': '#d0b39d',
            'track_pending': '#7f7367',
            'track_done': '#2e8b57',
            'track_error': '#c83c2f',
            'menu_bg': '#fff7ef',
            'menu_hover': '#eadccf',
            'menu_fg': '#201815',
        }

    return {
        'window_bg': '#0b0c0f',
        'card_bg': '#121318',
        'card_edge': '#272930',
        'card_title': '#c7a39f',
        'text_primary': '#f5efee',
        'text_secondary': '#dbc8c5',
        'text_muted': '#b39591',
        'text_subtle': '#7b6461',
        'title_accent': '#ff4f3f',
        'title_text': '#f5efee',
        'dot': '#0b0c0f',
        'input_bg': '#1c1f26',
        'input_border': '#5e6572',
        'input_text': '#f3e7e6',
        'button_bg': '#262932',
        'button_hover': '#353a46',
        'button_text': '#f2e1df',
        'danger': '#ff4f3f',
        'danger_hover': '#ff685b',
        'warning': '#9c6b1a',
        'warning_hover': '#b47c20',
        'warning_text': '#ffe5ae',
        'accent': '#ff614f',
        'accent_hover': '#ff7a69',
        'accent_soft': '#7b2c25',
        'accent_soft_hover': '#944036',
        'accent_text': '#fff6f4',
        'success': '#59c179',
        'error': '#ff7a73',
        'progress_track': '#3d414b',
        'info_bg': '#1a1d25',
        'info_edge': '#323a4c',
        'warning_bg': '#6c5600',
        'warning_fg': '#fff2a8',
        'track_bg': '#161a22',
        'track_badge_bg': '#1f2430',
        'track_active_bg': '#1f2430',
        'track_active_edge': '#485067',
        'track_pending': '#8a8f99',
        'track_done': '#75d796',
        'track_error': '#ff7a73',
        'menu_bg': '#1f2330',
        'menu_hover': '#363b49',
        'menu_fg': '#ebe1df',
    }


# ─────────────────────────────────────────────────
#  yt-dlp logger (sessiz — ui'a yansıtmıyoruz)
# ─────────────────────────────────────────────────
class _Logger:
    def __init__(self, fn=None):
        self._fn = fn or (lambda m: None)

    def debug(self, m):
        pass

    def info(self, m):
        self._fn(m)

    def warning(self, m):
        pass

    def error(self, m):
        self._fn(f'✗ {m}')


# ─────────────────────────────────────────────────
#  Tek track satırı
# ─────────────────────────────────────────────────
class TrackRow(ctk.CTkFrame):
    _ICON  = {'pending': '⏳', 'downloading': '⬇', 'done': '✓', 'error': '✗'}
    def __init__(self, parent, idx: int, title: str, palette: dict[str, str], **kwargs):
        self._palette = palette
        super().__init__(
            parent,
            corner_radius=8,
            fg_color=self._palette['track_bg'],
            border_width=1,
            border_color=self._palette['card_edge'],
            **kwargs,
        )
        self.grid_columnconfigure(2, weight=1)

        # ── Index badge
        badge = ctk.CTkFrame(self, fg_color=self._palette['track_badge_bg'], corner_radius=5, width=42, height=28)
        badge.grid(row=0, column=0, padx=(12, 8), pady=11)
        badge.grid_propagate(False)
        ctk.CTkLabel(
            badge,
            text=f'{idx:03d}',
            font=ctk.CTkFont(size=12, family='Consolas'),
            text_color=self._palette['text_subtle'],
        ).place(relx=0.5, rely=0.5, anchor='center')

        # ── Status icon
        self._icon = ctk.CTkLabel(
            self,
            text='⏳',
            font=ctk.CTkFont(size=16),
            text_color=self._palette['track_pending'],
            width=24,
        )
        self._icon.grid(row=0, column=1, padx=(0, 10))

        # ── Title
        short = (title[:65] + '…') if len(title) > 65 else title
        self._title = ctk.CTkLabel(
            self,
            text=short,
            font=ctk.CTkFont(size=14),
            text_color=self._palette['text_muted'],
            anchor='w',
        )
        self._title.grid(row=0, column=2, sticky='ew')

        # ── Progress / info
        self._info = ctk.CTkLabel(
            self,
            text='',
            font=ctk.CTkFont(size=12, family='Consolas'),
            text_color=self._palette['text_muted'],
            width=200,
            anchor='e',
        )
        self._info.grid(row=0, column=3, padx=(10, 16))

    def set_title(self, title: str):
        short = (title[:65] + '…') if len(title) > 65 else title
        self._title.configure(text=short)

    def update_status(self, status: str, pct: float = 0.0, extra: str = ''):
        icon  = self._ICON.get(status, '?')
        color = {
            'pending': self._palette['track_pending'],
            'downloading': self._palette['accent'],
            'done': self._palette['track_done'],
            'error': self._palette['track_error'],
        }.get(status, self._palette['track_pending'])
        tc = {
            'pending': self._palette['text_muted'],
            'downloading': self._palette['text_primary'],
            'done': self._palette['text_secondary'],
            'error': self._palette['track_error'],
        }.get(status, self._palette['text_muted'])

        self._icon.configure(text=icon, text_color=color)
        self._title.configure(text_color=tc)

        if status == 'downloading':
            filled = int(pct * 20)
            bar = '█' * filled + '░' * (20 - filled)
            self._info.configure(
                text=f'{pct * 100:5.1f}%  {bar}',
                text_color=self._palette['accent'],
            )
            self.configure(
                fg_color=self._palette['track_active_bg'],
                border_color=self._palette['track_active_edge'],
            )
        elif status == 'done':
            self._info.configure(text=extra or '✓', text_color=self._palette['track_done'])
            self.configure(
                fg_color=self._palette['track_bg'],
                border_color=self._palette['card_edge'],
            )
        elif status == 'error':
            self._info.configure(text='error', text_color=self._palette['track_error'])
            self.configure(border_color=self._palette['track_error'])
        else:
            self._info.configure(text='')
            self.configure(
                fg_color=self._palette['track_bg'],
                border_color=self._palette['card_edge'],
            )


# ─────────────────────────────────────────────────
#  Ana uygulama
# ─────────────────────────────────────────────────
class App(ctk.CTk):
    # ── Renk paleti ──
    # Tam ekranda içerik genişliği
    MAX_W = 1680

    def __init__(self):
        super().__init__()
        self._locales = load_locales()
        self._config = load_config()
        self._lang = normalize_language(self._config.get('language'), self._locales)
        self._theme = str(self._config.get('theme', 'dark')).lower()
        if self._theme not in {'dark', 'light', 'system'}:
            self._theme = 'dark'
        ctk.set_appearance_mode(self._theme)
        self._apply_theme_palette()
        self.title(self._tr('app.title'))
        self.geometry('960x820')
        self.minsize(700, 640)
        self.resizable(True, True)
        self.configure(fg_color=self._palette['window_bg'])

        self._download_folder = os.path.join(os.path.expanduser('~'), 'Downloads')
        self._log_queue: queue.Queue = queue.Queue()
        self._media_type = 'video'
        self._fmt = 'mp4'
        self._track_rows: dict[int, TrackRow] = {}
        self._track_files: dict[int, str] = {}
        self._current_dl_idx: int | None = None
        self._pl_total = 0
        self._last_download_path = ''
        self._is_downloading = False
        self._cancel_event = threading.Event()
        self._batch_total = 0
        self._batch_index = 0
        self._batch_urls: dict[int, str] = {}
        self._dnd_available = False
        self._preview_loading = False
        self._wide_layout = False
        self._content_width = 0
        self._latest_app_release_url: str | None = None
        self._latest_ytdlp_version: str | None = None
        self._ffmpeg_location, self._ffmpeg_source = resolve_ffmpeg_location()
        self._ffmpeg_available = bool(self._ffmpeg_location)
        self._type_video_label = self._tr('type.video')
        self._type_audio_label = self._tr('type.audio')

        # ── Centered container — tam ekranda max genişlik sınırlı ──
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._layout_root = ctk.CTkFrame(self, fg_color='transparent')
        self._layout_root.grid(row=0, column=0, sticky='nsew')
        self._layout_root.grid_columnconfigure(0, weight=1)
        self._layout_root.grid_rowconfigure(0, weight=1)

        self._content_scroll = ctk.CTkScrollableFrame(
            self._layout_root,
            fg_color='transparent',
            corner_radius=0,
            border_width=0,
        )
        self._content_scroll.grid(row=0, column=0, sticky='nsew', padx=24, pady=(0, 10))
        self._content_scroll.grid_columnconfigure(0, weight=1)

        self._container = self._content_scroll
        self._container.grid_columnconfigure(0, weight=1)
        self._container.grid_rowconfigure(1, weight=1)

        self._action_bar = ctk.CTkFrame(self._layout_root, fg_color='transparent')
        self._action_bar.grid(row=1, column=0, sticky='ew', padx=24, pady=(0, 18))
        self._action_bar.grid_columnconfigure(0, weight=1)

        self.bind('<Configure>', self._on_resize)

        self._build_all()
        self._bind_shortcuts()
        self._poll()
        self.after(400, self._start_update_checks)

    def _on_resize(self, event=None):
        """Tam ekranda container'ı ortala ve max genişliği sınırla."""
        if not self.winfo_exists() or not hasattr(self, '_content_scroll') or not self._content_scroll.winfo_exists():
            return
        w = int(getattr(event, 'width', 0) or self.winfo_width())
        if w > self.MAX_W + 48:
            pad_x = (w - self.MAX_W) // 2
        else:
            pad_x = 24
        self._content_width = max(320, w - (pad_x * 2) - 16)
        try:
            self._content_scroll.grid_configure(padx=pad_x)
            self._action_bar.grid_configure(padx=pad_x)
            self._apply_responsive_layout(self._content_width)
        except tk.TclError:
            return

    def _apply_responsive_layout(self, content_width: int):
        if not hasattr(self, '_body_grid'):
            return
        self._wide_layout = use_wide_layout(content_width)
        for widget in (self._left_column, self._right_column):
            widget.grid_forget()
        if self._wide_layout:
            self._body_grid.grid_columnconfigure(0, weight=7, uniform='content')
            self._body_grid.grid_columnconfigure(1, weight=5, uniform='content')
            self._left_column.grid(row=0, column=0, sticky='nsew', padx=(0, 10))
            self._right_column.grid(row=0, column=1, sticky='nsew', padx=(10, 0))
        else:
            self._body_grid.grid_columnconfigure(0, weight=1)
            self._body_grid.grid_columnconfigure(1, weight=0)
            self._left_column.grid(row=0, column=0, sticky='nsew')
            self._right_column.grid(row=1, column=0, sticky='nsew', pady=(2, 0))

    def _tr(self, key: str, **kwargs) -> str:
        return tr(self._locales, self._lang, key, **kwargs)

    def _language_choices(self) -> dict[str, str]:
        return {
            self._tr('language.tr'): 'tr',
            self._tr('language.en'): 'en',
        }

    def _theme_choices(self) -> dict[str, str]:
        return {
            self._tr('theme.dark'): 'dark',
            self._tr('theme.light'): 'light',
            self._tr('theme.system'): 'system',
        }

    def _active_theme_mode(self) -> str:
        return 'light' if ctk.get_appearance_mode().lower() == 'light' else 'dark'

    def _apply_theme_palette(self):
        self._palette = resolve_theme_palette(self._active_theme_mode())
        self.C_RED = self._palette['danger']
        self.C_RED_HOV = self._palette['danger_hover']
        self.C_BTN = self._palette['button_bg']
        self.C_BTN_HOV = self._palette['button_hover']
        self.C_SUCCESS = self._palette['success']
        self.C_ERR = self._palette['error']
        self.C_OPT_BG = self._palette['input_bg']
        self.C_OPT_BTN = self._palette['button_bg']
        self.C_OPT_HOV = self._palette['button_hover']
        self.C_OPT_DRP = self._palette['card_bg']
        self.C_CARD_BG = self._palette['card_bg']
        self.C_BORDER = self._palette['card_edge']
        self.configure(fg_color=self._palette['window_bg'])

    def _style_segmented_button(self, widget: ctk.CTkSegmentedButton):
        widget.configure(
            fg_color=self._palette['input_bg'],
            unselected_color=self._palette['input_bg'],
            unselected_hover_color=self._palette['button_hover'],
            selected_color=self._palette['danger'],
            selected_hover_color=self._palette['danger_hover'],
            text_color=self._palette['button_text'],
            text_color_disabled=self._palette['text_subtle'],
        )

    def _set_language(self, choice: str):
        lang = self._language_choices().get(choice)
        if not lang or lang == self._lang:
            return
        self._lang = lang
        self._config['language'] = lang
        save_config(self._config)
        self._type_video_label = self._tr('type.video')
        self._type_audio_label = self._tr('type.audio')
        self._rebuild_ui()

    def _set_theme(self, choice: str):
        theme = self._theme_choices().get(choice)
        if not theme or theme == self._theme:
            return
        self._theme = theme
        self._config['theme'] = theme
        ctk.set_appearance_mode(theme)
        self._apply_theme_palette()
        save_config(self._config)
        self._rebuild_ui()

    def _rebuild_ui(self):
        for host in (self._container, self._action_bar):
            for child in host.winfo_children():
                child.destroy()
        self._track_rows.clear()
        self._track_files.clear()
        self._current_dl_idx = None
        self._pl_total = 0
        self._last_download_path = ''
        self.title(self._tr('app.title'))
        self._apply_theme_palette()
        self._build_all()
        self._bind_shortcuts()

    def _bind_shortcuts(self):
        self.bind_all('<Control-v>', self._shortcut_paste)
        self.bind_all('<Control-V>', self._shortcut_paste)
        self.bind_all('<Control-Return>', self._shortcut_start)
        self.bind_all('<Escape>', self._shortcut_cancel)
        self.bind_all('<Control-l>', self._shortcut_clear_focus)
        self.bind_all('<Control-L>', self._shortcut_clear_focus)

    def _shortcut_paste(self, _event=None):
        self._paste()
        return 'break'

    def _shortcut_start(self, _event=None):
        self.start_download()
        return 'break'

    def _shortcut_cancel(self, _event=None):
        self.cancel_download()
        return 'break'

    def _shortcut_clear_focus(self, _event=None):
        self._clear_url_text()
        return 'break'

    # ─────────────────────────────────────────────
    #  UI Yardımcıları
    # ─────────────────────────────────────────────
    def _card(self, parent, row: int, title: str = '', expand: bool = False) -> ctk.CTkFrame:
        card = ctk.CTkFrame(
            parent,
            corner_radius=16,
            fg_color=self.C_CARD_BG,
            border_width=1,
            border_color=self.C_BORDER,
        )
        card.grid(
            row=row, column=0,
            padx=0, pady=(4, 4),
            sticky='nsew' if expand else 'ew',
        )
        card.grid_columnconfigure(0, weight=1)
        if expand:
            card.grid_rowconfigure(1, weight=1)
        if title:
            ctk.CTkLabel(
                card, text=title,
                font=ctk.CTkFont(size=13, weight='bold'),
                text_color=self._palette['card_title'],
            ).grid(row=0, column=0, padx=18, pady=(12, 2), sticky='w')
        return card

    def _omenu(self, parent, values, var, **gkw) -> ctk.CTkOptionMenu:
        m = ctk.CTkOptionMenu(
            parent, values=values, variable=var,
            height=36, corner_radius=10,
            fg_color=self.C_OPT_BG,
            button_color=self.C_OPT_BTN,
            button_hover_color=self.C_OPT_HOV,
            dropdown_fg_color=self.C_OPT_DRP,
            text_color=self._palette['button_text'],
            font=ctk.CTkFont(size=13),
        )
        m.grid(**gkw)
        return m

    # ─────────────────────────────────────────────
    #  Sağ tık context menüsü
    # ─────────────────────────────────────────────
    def _bind_context_menu(self, entry):
        """Entry/Textbox widget'ına sağ tık menüsü bağla."""
        inner = getattr(entry, '_entry', None) or getattr(entry, '_textbox', None)
        if inner is None:
            return
        inner.bind('<Button-3>', lambda e: self._show_context_menu(e, entry))

    def _show_context_menu(self, event, entry):
        inner = getattr(entry, '_entry', None) or getattr(entry, '_textbox', None)
        if inner is None:
            return
        menu = tk.Menu(
            self, tearoff=0,
            bg=self._palette['menu_bg'], fg=self._palette['menu_fg'],
            activebackground=self._palette['menu_hover'], activeforeground=self._palette['text_primary'],
            font=('Segoe UI', 10),
            relief='flat', bd=1,
        )
        menu.add_command(
            label=f"  {self._tr('menu.cut')}",
            command=lambda: self._ctx_cut(inner),
        )
        menu.add_command(
            label=f"  {self._tr('menu.copy')}",
            command=lambda: self._ctx_copy(inner),
        )
        menu.add_command(
            label=f"  {self._tr('menu.paste')}",
            command=lambda: self._ctx_paste(entry),
        )
        menu.add_separator()
        menu.add_command(
            label=f"  {self._tr('menu.select_all')}",
            command=lambda: self._ctx_select_all(inner),
        )
        menu.add_separator()
        menu.add_command(
            label=f"  {self._tr('menu.clear')}",
            command=lambda: self._clear_widget_text(entry),
        )
        menu.tk_popup(event.x_root, event.y_root)

    def _ctx_cut(self, inner):
        try:
            if hasattr(inner, 'selection_present') and not inner.selection_present():
                return
        except Exception:
            pass
        inner.event_generate('<<Cut>>')

    def _ctx_copy(self, inner):
        try:
            if hasattr(inner, 'selection_present') and not inner.selection_present():
                return
        except Exception:
            pass
        inner.event_generate('<<Copy>>')

    def _ctx_paste(self, entry):
        try:
            text = self.clipboard_get()
            if text:
                entry.insert('insert', text.strip())
        except Exception:
            pass

    def _ctx_select_all(self, inner):
        try:
            inner.tag_add('sel', '1.0', 'end')
            inner.mark_set('insert', 'end')
        except Exception:
            inner.select_range(0, 'end')
            inner.icursor('end')

    # ─────────────────────────────────────────────
    #  Bölüm inşaları
    # ─────────────────────────────────────────────
    def _build_all(self):
        self._header_host = ctk.CTkFrame(self._container, fg_color='transparent')
        self._header_host.grid(row=0, column=0, sticky='ew')
        self._header_host.grid_columnconfigure(0, weight=1)

        self._body_grid = ctk.CTkFrame(self._container, fg_color='transparent')
        self._body_grid.grid(row=1, column=0, sticky='nsew')
        self._body_grid.grid_columnconfigure(0, weight=1)
        self._body_grid.grid_rowconfigure(0, weight=1)
        self._body_grid.grid_rowconfigure(1, weight=1)

        self._left_column = ctk.CTkFrame(self._body_grid, fg_color='transparent')
        self._left_column.grid_columnconfigure(0, weight=1)
        self._left_column.grid_rowconfigure(3, weight=1)

        self._right_column = ctk.CTkFrame(self._body_grid, fg_color='transparent')
        self._right_column.grid_columnconfigure(0, weight=1)
        self._right_column.grid_rowconfigure(2, weight=1)

        self._build_header(self._header_host)
        self._build_url(self._left_column, 0)
        self._build_save_path(self._left_column, 1)
        self._build_progress(self._left_column, 2)
        self._build_tracklist(self._left_column, 3)
        self._build_type_format(self._right_column, 0)
        self._build_options(self._right_column, 1)
        self._on_type(self._type_seg.get())
        self._build_dl_button()
        self._build_history_panel(self._right_column, 2)
        self._apply_responsive_layout(self._content_width or self.winfo_width())

    # ── Başlık ──────────────────────────────────
    def _build_header(self, parent):
        hf = ctk.CTkFrame(parent, fg_color='transparent')
        hf.grid(row=0, column=0, padx=4, pady=(20, 10), sticky='ew')
        hf.grid_columnconfigure(0, weight=1)

        title_frame = ctk.CTkFrame(hf, fg_color='transparent')
        title_frame.grid(row=0, column=0, sticky='w')

        ctk.CTkLabel(
            title_frame, text='YT DOWNLOADER',
            font=ctk.CTkFont(size=22, weight='bold'),
            text_color=self._palette['title_accent'],
        ).pack(side='left', padx=(0, 12))

        ctk.CTkLabel(
            title_frame, text=self._tr('header.engine').upper(),
            font=ctk.CTkFont(size=11, weight='bold'),
            text_color=self._palette['text_subtle'],
        ).pack(side='left')

        right_frame = ctk.CTkFrame(hf, fg_color='transparent')
        right_frame.grid(row=0, column=1, sticky='e')

        info_frame = ctk.CTkFrame(right_frame, fg_color='transparent')
        info_frame.grid(row=0, column=0, sticky='e')

        ctk.CTkLabel(
            info_frame, text=f'v{__version__}',
            font=ctk.CTkFont(size=13, weight='bold'),
            text_color=self._palette['text_subtle'],
        ).pack(side='left', padx=(0, 8))

        ctk.CTkLabel(
            info_frame, text='•',
            font=ctk.CTkFont(size=13),
            text_color=self._palette['dot'],
        ).pack(side='left', padx=(0, 8))

        ctk.CTkLabel(
            info_frame, text='',
            font=ctk.CTkFont(size=13),
            text_color=self._palette['text_subtle'],
        ).pack(side='left')

        self._header_pref_bar = ctk.CTkFrame(
            right_frame,
            fg_color=self._palette['card_bg'],
            corner_radius=10,
            border_width=1,
            border_color=self._palette['card_edge'],
        )
        self._header_pref_bar.grid(row=1, column=0, pady=(10, 0), sticky='e')

        theme_choices = self._theme_choices()
        selected_theme = next((name for name, code in theme_choices.items() if code == self._theme), list(theme_choices)[0])
        self._theme_var = ctk.StringVar(value=selected_theme)
        self._theme_menu = self._build_header_pref_selector(
            self._header_pref_bar,
            0,
            self._tr('label.theme'),
            list(theme_choices.keys()),
            self._theme_var,
            self._set_theme,
        )

        language_choices = self._language_choices()
        selected_lang = next((name for name, code in language_choices.items() if code == self._lang), list(language_choices)[0])
        self._lang_var = ctk.StringVar(value=selected_lang)
        self._lang_menu = self._build_header_pref_selector(
            self._header_pref_bar,
            1,
            self._tr('label.language'),
            list(language_choices.keys()),
            self._lang_var,
            self._set_language,
        )

        if not self._ffmpeg_available:
            warn = ctk.CTkFrame(
                hf,
                fg_color=self._palette['warning_bg'],
                corner_radius=8,
            )
            warn.grid(row=1, column=0, columnspan=2, pady=(12, 0), sticky='ew')
            warn.grid_columnconfigure(1, weight=1)

            icon = ctk.CTkLabel(
                warn,
                text='⚠',
                font=ctk.CTkFont(size=15, weight='bold'),
                text_color=self._palette['warning_fg'],
            )
            icon.grid(row=0, column=0, padx=(10, 8), pady=8)

            text = ctk.CTkLabel(
                warn,
                text=self._tr('warning.ffmpeg_missing'),
                font=ctk.CTkFont(size=12),
                text_color=self._palette['warning_fg'],
                anchor='w',
                justify='left',
            )
            text.grid(row=0, column=1, padx=(0, 10), pady=8, sticky='ew')

            for widget in (warn, icon, text):
                widget.bind('<Button-1>', self._open_ffmpeg_download)

        self._build_update_notices(hf)

    # ── URL ─────────────────────────────────────
    def _build_header_pref_selector(self, parent, column: int, label: str, values, variable, command):
        wrapper = ctk.CTkFrame(parent, fg_color='transparent')
        wrapper.grid(row=0, column=column, padx=(10, 10), pady=8, sticky='ew')
        ctk.CTkLabel(
            wrapper,
            text=label,
            font=ctk.CTkFont(size=11, weight='bold'),
            text_color=self._palette['card_title'],
        ).grid(row=0, column=0, sticky='w', pady=(0, 4))
        menu = self._omenu(wrapper, values, variable, row=1, column=0, sticky='ew')
        menu.configure(width=138, height=32, command=command)
        return menu

    def _build_update_notices(self, parent):
        self._update_notice_frame = ctk.CTkFrame(
            parent,
            fg_color=self._palette['info_bg'],
            corner_radius=8,
            border_width=1,
            border_color=self._palette['info_edge'],
        )
        self._update_notice_frame.grid(row=2, column=0, columnspan=2, pady=(10, 0), sticky='ew')
        self._update_notice_frame.grid_columnconfigure(0, weight=1)
        self._update_notice_frame.grid_remove()

        self._ytdlp_notice = ctk.CTkFrame(self._update_notice_frame, fg_color='transparent')
        self._ytdlp_notice.grid(row=0, column=0, padx=10, pady=(8, 2), sticky='ew')
        self._ytdlp_notice.grid_columnconfigure(0, weight=1)
        self._ytdlp_notice.grid_remove()
        self._ytdlp_notice_label = ctk.CTkLabel(
            self._ytdlp_notice,
            text=self._tr('update.ytdlp.available'),
            font=ctk.CTkFont(size=12),
            text_color=self._palette['text_primary'],
            anchor='w',
        )
        self._ytdlp_notice_label.grid(row=0, column=0, sticky='w')
        self._ytdlp_notice_btn = ctk.CTkButton(
            self._ytdlp_notice,
            text=self._tr('update.ytdlp.button'),
            width=118,
            height=30,
            corner_radius=7,
            command=self._run_ytdlp_update,
            fg_color=self.C_BTN,
            hover_color=self.C_BTN_HOV,
            text_color=self._palette['button_text'],
            font=ctk.CTkFont(size=12),
        )
        self._ytdlp_notice_btn.grid(row=0, column=1, padx=(10, 0))

        self._app_notice = ctk.CTkFrame(self._update_notice_frame, fg_color='transparent')
        self._app_notice.grid(row=1, column=0, padx=10, pady=(2, 8), sticky='ew')
        self._app_notice.grid_columnconfigure(0, weight=1)
        self._app_notice.grid_remove()
        self._app_notice_label = ctk.CTkLabel(
            self._app_notice,
            text=self._tr('update.app.available'),
            font=ctk.CTkFont(size=12),
            text_color=self._palette['text_primary'],
            anchor='w',
        )
        self._app_notice_label.grid(row=0, column=0, sticky='w')
        self._app_notice_btn = ctk.CTkButton(
            self._app_notice,
            text=self._tr('update.app.button'),
            width=118,
            height=30,
            corner_radius=7,
            command=self._open_latest_release_page,
            fg_color=self.C_BTN,
            hover_color=self.C_BTN_HOV,
            text_color=self._palette['button_text'],
            font=ctk.CTkFont(size=12),
        )
        self._app_notice_btn.grid(row=0, column=1, padx=(10, 0))

    def _refresh_update_notice_visibility(self):
        if self._ytdlp_notice.winfo_ismapped() or self._app_notice.winfo_ismapped():
            self._update_notice_frame.grid()
        else:
            self._update_notice_frame.grid_remove()

    def _build_url(self, parent, row: int):
        card = self._card(parent, row, self._tr('url.label'))
        self._url_card = card
        inner = ctk.CTkFrame(card, fg_color='transparent')
        inner.grid(row=1, column=0, padx=18, pady=(4, 14), sticky='ew')
        inner.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            inner,
            text=self._tr('url.placeholder'),
            font=ctk.CTkFont(size=11),
            text_color=self._palette['text_subtle'],
        ).grid(row=0, column=0, sticky='w', pady=(0, 6), columnspan=2)

        row = ctk.CTkFrame(inner, fg_color='transparent')
        row.grid(row=1, column=0, sticky='ew', columnspan=2)
        row.grid_columnconfigure(0, weight=1)

        self.url_entry = ctk.CTkTextbox(
            row,
            height=54,
            font=ctk.CTkFont(size=14),
            corner_radius=12,
            border_width=1,
            fg_color=self._palette['input_bg'],
            border_color=self._palette['input_border'],
            text_color=self._palette['input_text'],
        )
        self.url_entry.grid(row=0, column=0, sticky='ew')
        self.url_entry.insert('1.0', '')
        self.url_entry.bind('<Control-Return>', lambda _: self.start_download())
        self._bind_context_menu(self.url_entry)

        btns = ctk.CTkFrame(row, fg_color='transparent')
        btns.grid(row=0, column=1, padx=(8, 0), sticky='n')

        ctk.CTkButton(
            btns, text=self._tr('button.paste'), width=90, height=40,
            command=self._paste, corner_radius=12,
            fg_color=self.C_BTN, hover_color=self.C_BTN_HOV,
            font=ctk.CTkFont(size=13, weight='bold'),
            text_color=self._palette['button_text'],
        ).pack(side='left', padx=(0, 5))

        ctk.CTkButton(
            btns, text=self._tr('button.fetch_info'), width=102, height=40,
            command=self._start_preview_fetch,
            corner_radius=12,
            fg_color=self.C_BTN, hover_color=self.C_BTN_HOV,
            font=ctk.CTkFont(size=13, weight='bold'),
            text_color=self._palette['button_text'],
        ).pack(side='left', padx=(0, 5))

        ctk.CTkButton(
            btns, text='✕', width=46, height=46,
            command=self._clear_url_text,
            corner_radius=12,
            fg_color=self.C_BTN, hover_color=self.C_RED_HOV,
            font=ctk.CTkFont(size=15, weight='bold'),
            text_color=self._palette['button_text'],
        ).pack(side='left')

        self._url_summary = ctk.CTkLabel(
            inner,
            text=self._tr('fetch_summary.idle'),
            anchor='w',
            justify='left',
            font=ctk.CTkFont(size=11),
            text_color=self._palette['text_subtle'],
        )
        self._url_summary.grid(row=2, column=0, columnspan=2, sticky='ew', pady=(8, 0))

        self._setup_url_drag_drop()

    def _setup_url_drag_drop(self):
        self._dnd_available = False
        if DND_TEXT is None:
            return
        try:
            self.url_entry.drop_target_register(DND_TEXT)
            self.url_entry.dnd_bind('<<Drop>>', self._on_url_drop)
            self._dnd_available = True
        except Exception:
            self._dnd_available = False

    def _extract_urls_from_drop(self, payload: str) -> list[str]:
        if not payload:
            return []
        matches = re.findall(r'https?://\S+', payload, flags=re.IGNORECASE)
        cleaned: list[str] = []
        for match in matches:
            url = match.strip().strip('{}').rstrip(',;')
            if url and url not in cleaned:
                cleaned.append(url)
        return cleaned

    def _on_url_drop(self, event):
        urls = self._extract_urls_from_drop(getattr(event, 'data', ''))
        if not urls:
            return
        existing = [u.strip() for u in self._get_url_text().splitlines() if u.strip()]
        merged = existing + [u for u in urls if u not in existing]
        self._set_url_text('\n'.join(merged))

    def _start_preview_fetch(self):
        raw = self._get_url_text()
        urls = [u.strip() for u in raw.splitlines() if u.strip()]
        url = next((u for u in urls if is_valid_download_url(u)), '')
        if not url:
            self._url_summary.configure(text=self._tr('status.invalid_url'), text_color=self.C_ERR)
            return
        if self._preview_loading:
            return

        self._preview_loading = True
        self._url_summary.configure(
            text=self._tr('fetch_summary.loading'),
            text_color=self._palette['text_muted'],
        )
        threading.Thread(target=self._preview_worker, args=(url,), daemon=True).start()

    def _preview_worker(self, url: str):
        try:
            import yt_dlp
        except ImportError:
            self._q('preview_error', self._tr('error.ytdlp_missing'))
            return

        opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
        }
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
            if isinstance(info, dict) and info.get('_type') == 'playlist':
                entries = info.get('entries') or []
                info = next((e for e in entries if isinstance(e, dict)), info)

            title = (info or {}).get('title') or url
            duration = (info or {}).get('duration')
            channel = (info or {}).get('channel') or (info or {}).get('uploader') or '—'
            self._q('preview_data', summarize_media_info(info, url))
        except Exception as exc:
            self._q('preview_error', self._tr(map_download_exception_key(exc)))

    def _download_thumbnail_data(self, image_url: str) -> str | None:
        req = urlrequest.Request(image_url, headers={'User-Agent': 'yt-downloader-gui/3.1'})
        try:
            with urlrequest.urlopen(req, timeout=5) as response:
                raw = response.read()
        except Exception:
            return None
        if not raw:
            return None
        return base64.b64encode(raw).decode('ascii')

    def _format_duration(self, seconds: int | float | None) -> str:
        if not isinstance(seconds, (int, float)) or seconds < 0:
            return '—'
        total = int(seconds)
        h, rem = divmod(total, 3600)
        m, s = divmod(rem, 60)
        if h:
            return f'{h}:{m:02d}:{s:02d}'
        return f'{m}:{s:02d}'

    def _animate_preview_spinner(self):
        if not self.winfo_exists():
            return
        if not self._preview_loading:
            self._preview_spinner.configure(text='')
            return
        frames = ('⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏')
        self._preview_spinner.configure(text=frames[self._preview_spinner_phase % len(frames)])
        self._preview_spinner_phase += 1
        self.after(100, self._animate_preview_spinner)

    def _show_preview_data(self, title: str, duration: int | float | None, channel: str, thumb_data: str | None):
        self._preview_loading = False
        self._preview_title.configure(text=title)
        self._preview_meta.configure(
            text=self._tr(
                'preview.meta',
                duration=self._format_duration(duration),
                channel=channel,
            )
        )
        self._preview_status.configure(text=self._tr('preview.ready'), text_color=self.C_SUCCESS)
        if thumb_data:
            try:
                self._preview_img = tk.PhotoImage(data=thumb_data)
                self._preview_thumb.configure(image=self._preview_img, text='')
            except Exception:
                self._preview_thumb.configure(image=None, text=self._tr('preview.no_thumb'))
        else:
            self._preview_thumb.configure(image=None, text=self._tr('preview.no_thumb'))

    def _show_preview_error(self, message: str):
        self._preview_loading = False
        self._preview_status.configure(text=message, text_color=self.C_ERR)

    # ── Tür + Format (tek kart) ──────────────────
    def _build_type_format(self, parent, row: int):
        card = self._card(parent, row, self._tr('card.mode_format'))
        self._mode_card = card

        inner = ctk.CTkFrame(card, fg_color='transparent')
        inner.grid(row=1, column=0, padx=14, pady=(6, 12), sticky='ew')
        inner.grid_columnconfigure(1, weight=1)

        # Tür
        ctk.CTkLabel(
            inner, text=self._tr('label.type'),
            font=ctk.CTkFont(size=12, weight='bold'),
            text_color=self._palette['card_title'], width=60,
        ).grid(row=0, column=0, sticky='w', padx=(0, 14))

        self._type_seg = ctk.CTkSegmentedButton(
            inner,
            values=[self._type_video_label, self._type_audio_label],
            command=self._on_type,
            font=ctk.CTkFont(size=13),
            height=34,
            corner_radius=10,
        )
        default_type = self._type_audio_label if self._media_type == 'audio' else self._type_video_label
        self._style_segmented_button(self._type_seg)
        self._type_seg.set(default_type)
        self._type_seg.grid(row=0, column=1, sticky='ew')

        # Format
        ctk.CTkLabel(
            inner, text=self._tr('label.format'),
            font=ctk.CTkFont(size=12, weight='bold'),
            text_color=self._palette['card_title'], width=60,
        ).grid(row=1, column=0, sticky='w', padx=(0, 14), pady=(10, 0))

        # Video formatları
        self._vfmt_frame = ctk.CTkFrame(inner, fg_color='transparent')
        self._vfmt_frame.grid(row=1, column=1, sticky='ew', pady=(10, 0))
        self._vfmt_seg = ctk.CTkSegmentedButton(
            self._vfmt_frame,
            values=['MP4', 'WEBM', 'MKV'],
            command=lambda v: setattr(self, '_fmt', v.lower()),
            font=ctk.CTkFont(size=13), height=34,
            corner_radius=10,
        )
        self._style_segmented_button(self._vfmt_seg)
        self._vfmt_seg.set('MP4')
        self._vfmt_seg.pack(fill='x')

        # Ses formatları
        self._afmt_frame = ctk.CTkFrame(inner, fg_color='transparent')
        self._afmt_frame.grid(row=1, column=1, sticky='ew', pady=(10, 0))
        self._afmt_seg = ctk.CTkSegmentedButton(
            self._afmt_frame,
            values=['MP3', 'OPUS', 'FLAC', 'M4A', 'WAV'],
            command=lambda v: setattr(self, '_fmt', v.lower()),
            font=ctk.CTkFont(size=13), height=34,
            corner_radius=10,
        )
        self._style_segmented_button(self._afmt_seg)
        self._afmt_seg.set('MP3')
        self._afmt_seg.pack(fill='x')
        self._afmt_frame.grid_remove()

    # ── Ayarlar ──────────────────────────────────
    def _build_options(self, parent, row: int):
        self._settings_card = self._card(parent, row, self._tr('card.media_options'))
        card = self._settings_card

        # ── Video ayarları
        self._v_opts = ctk.CTkFrame(card, fg_color='transparent')
        self._v_opts.grid(row=1, column=0, padx=14, pady=(4, 12), sticky='ew')
        for c in range(4):
            self._v_opts.grid_columnconfigure(c, weight=1)

        self._res_var    = ctk.StringVar(value=self._tr('opt.best'))
        self._vcodec_var = ctk.StringVar(value=self._tr('opt.auto'))
        self._fps_var    = ctk.StringVar(value=self._tr('opt.unlimited'))
        self._hdr_var    = ctk.StringVar(value=self._tr('opt.hdr_include'))

        v_fields = [
            (self._tr('opt.resolution'),
             [self._tr('opt.best'), '4320p (8K)', '2160p (4K)', '1440p (2K)',
              '1080p', '720p', '480p', '360p', '240p'],
             self._res_var),
            (self._tr('opt.video_codec'),
             [self._tr('opt.auto'), 'h264 (AVC)', 'h265 (HEVC)', 'VP9', 'AV1'],
             self._vcodec_var),
            (self._tr('opt.max_fps'),
             [self._tr('opt.unlimited'), '60', '30', '24'],
             self._fps_var),
            (self._tr('opt.hdr'),
             [self._tr('opt.hdr_include'), self._tr('opt.hdr_sdr_only')],
             self._hdr_var),
        ]
        for col, (lbl, vals, var) in enumerate(v_fields):
            px = (0 if col == 0 else 8, 0)
            ctk.CTkLabel(
                self._v_opts, text=lbl,
                font=ctk.CTkFont(size=11), text_color=self._palette['text_muted'],
            ).grid(row=0, column=col, padx=px, sticky='w', pady=(0, 4))
            self._omenu(self._v_opts, vals, var,
                        row=1, column=col, padx=px, sticky='ew')

        # ── Ses ayarları
        self._a_opts = ctk.CTkFrame(card, fg_color='transparent')
        self._a_opts.grid(row=1, column=0, padx=14, pady=(4, 12), sticky='ew')
        for c in range(3):
            self._a_opts.grid_columnconfigure(c, weight=1)

        self._abitrate_var   = ctk.StringVar(value=self._tr('opt.audio_best_vbr'))
        self._samplerate_var = ctk.StringVar(value=self._tr('opt.auto'))
        self._channels_var   = ctk.StringVar(value=self._tr('opt.auto'))

        a_fields = [
            (self._tr('opt.audio_quality'),
             [self._tr('opt.audio_best_vbr'), '320k', '256k', '192k', '128k', '96k', '64k'],
             self._abitrate_var),
            (self._tr('opt.sample_rate'),
             [self._tr('opt.auto'), '48000 Hz', '44100 Hz', '22050 Hz'],
             self._samplerate_var),
            (self._tr('opt.channels'),
             [self._tr('opt.auto'), self._tr('opt.channel_stereo'), self._tr('opt.channel_mono')],
             self._channels_var),
        ]
        for col, (lbl, vals, var) in enumerate(a_fields):
            px = (0 if col == 0 else 8, 0)
            ctk.CTkLabel(
                self._a_opts, text=lbl,
                font=ctk.CTkFont(size=11), text_color=self._palette['text_muted'],
            ).grid(row=0, column=col, padx=px, sticky='w', pady=(0, 4))
            self._omenu(self._a_opts, vals, var,
                        row=1, column=col, padx=px, sticky='ew')

        self._a_opts.grid_remove()


    # ── Kayıt Yeri ───────────────────────────────
    def _build_save_path(self, parent, row: int):
        card = self._card(parent, row, self._tr('card.save_path'))
        self._save_card = card
        row = ctk.CTkFrame(card, fg_color='transparent')
        row.grid(row=1, column=0, padx=14, pady=(4, 12), sticky='ew')
        row.grid_columnconfigure(0, weight=1)

        self._out_entry = ctk.CTkEntry(
            row, height=36,
            font=ctk.CTkFont(size=13),
            corner_radius=10,
            border_width=1,
            fg_color=self._palette['input_bg'],
            border_color=self._palette['input_border'],
            text_color=self._palette['input_text'],
        )
        self._out_entry.insert(0, self._download_folder)
        self._out_entry.grid(row=0, column=0, sticky='ew')
        self._bind_context_menu(self._out_entry)

        ctk.CTkButton(
            row, text=self._tr('button.browse'), width=84, height=36,
            command=self._browse, corner_radius=10,
            fg_color=self.C_BTN, hover_color=self.C_BTN_HOV,
            font=ctk.CTkFont(size=13),
            text_color=self._palette['button_text'],
        ).grid(row=0, column=1, padx=(8, 0))

    # ── İndir Butonu ─────────────────────────────
    def _build_dl_button(self):
        action_row = ctk.CTkFrame(
            self._action_bar,
            corner_radius=16,
            fg_color=self.C_CARD_BG,
            border_width=1,
            border_color=self.C_BORDER,
        )
        action_row.grid(row=0, column=0, padx=0, pady=0, sticky='ew')
        action_row.grid_columnconfigure(0, weight=1)

        self._dl_btn = ctk.CTkButton(
            action_row,
            text=self._tr('button.download'),
            height=52,
            font=ctk.CTkFont(size=17, weight='bold'),
            command=self._on_main_button,
            fg_color=self.C_RED,
            hover_color=self.C_RED_HOV,
            corner_radius=14,
            text_color=self._palette['accent_text'],
        )
        self._dl_btn.grid(row=0, column=0, padx=14, pady=12, sticky='ew')

    def _on_main_button(self):
        if self._is_downloading:
            self.cancel_download()
        else:
            self.start_download()

    # ── İlerleme ─────────────────────────────────
    def _build_progress(self, parent, row: int):
        card = self._card(parent, row, self._tr('card.transfer_status'))
        self._progress_card = card

        prog_container = ctk.CTkFrame(card, fg_color='transparent')
        prog_container.grid(row=0, column=0, padx=16, pady=(14, 4), sticky='ew')
        prog_container.grid_columnconfigure(0, weight=1)

        self._prog_bar = ctk.CTkProgressBar(
            prog_container, height=10, corner_radius=10,
            fg_color=self._palette['progress_track'],
            progress_color=self.C_RED_HOV,
        )
        self._prog_bar.grid(row=0, column=0, sticky='ew')
        self._prog_bar.set(0)

        stats = ctk.CTkFrame(card, fg_color='transparent')
        stats.grid(row=1, column=0, padx=16, pady=(10, 12), sticky='ew')
        stats.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)

        def sl(text=None, bold=False):
            if text is None:
                text = self._tr('status.idle')
            return ctk.CTkLabel(
                stats, text=text,
                font=ctk.CTkFont(size=13, weight='bold' if bold else 'normal'),
                text_color=self._palette['text_muted'],
            )

        self._s_pct    = sl('0.0%', bold=True)
        self._s_speed  = sl()
        self._s_eta    = sl()
        self._s_size   = sl()
        self._s_status = sl()

        self._s_pct.grid(row=0, column=0, sticky='w')
        self._s_speed.grid(row=0, column=1)
        self._s_eta.grid(row=0, column=2)
        self._s_size.grid(row=0, column=3)
        self._s_status.grid(row=0, column=4, sticky='e')

        self._open_folder_btn = ctk.CTkButton(
            card,
            text=self._tr('button.open_folder'),
            height=34,
            command=self._open_last_folder,
            corner_radius=8,
            fg_color=self.C_BTN,
            hover_color=self.C_BTN_HOV,
            font=ctk.CTkFont(size=13),
            text_color=self._palette['button_text'],
        )
        self._open_folder_btn.grid(row=2, column=0, padx=16, pady=(0, 10), sticky='e')
        self._open_folder_btn.grid_remove()

    # ── Track Listesi ────────────────────────────
    def _build_tracklist(self, parent, row: int):
        card = self._card(parent, row, self._tr('card.current_stream'), expand=True)
        self._tracklist_card = card

        # Boş durum
        self._pl_empty = ctk.CTkFrame(card, fg_color='transparent')
        self._pl_empty.grid(row=1, column=0, pady=40, sticky='ew')

        ctk.CTkLabel(
            self._pl_empty,
            text='⬇',
            font=ctk.CTkFont(size=32),
            text_color=self._palette['text_subtle'],
        ).pack(pady=(0, 8))

        ctk.CTkLabel(
            self._pl_empty,
            text=self._tr('track.empty.title'),
            font=ctk.CTkFont(size=15, weight='bold'),
            text_color=self._palette['text_muted'],
        ).pack()

        ctk.CTkLabel(
            self._pl_empty,
            text=self._tr('track.empty.subtitle'),
            font=ctk.CTkFont(size=13),
            text_color=self._palette['text_subtle'],
        ).pack(pady=(4, 0))

        # Scrollable liste
        self._pl_scroll = ctk.CTkScrollableFrame(
            card,
            fg_color='transparent',
            corner_radius=0,
        )
        self._pl_scroll.grid_columnconfigure(0, weight=1)
        self._pl_scroll.grid(
            row=1, column=0, padx=8, pady=(0, 10), sticky='nsew'
        )
        self._pl_scroll.grid_remove()

    def _build_history_panel(self, parent, row: int):
        card = self._card(parent, row, self._tr('card.download_history'))
        self._history_card = card
        toolbar = ctk.CTkFrame(card, fg_color='transparent')
        toolbar.grid(row=1, column=0, padx=16, pady=(4, 8), sticky='ew')
        toolbar.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            toolbar,
            text=self._tr('history.subtitle'),
            font=ctk.CTkFont(size=11),
            text_color=self._palette['text_subtle'],
            anchor='w',
        ).grid(row=0, column=0, sticky='w')

        ctk.CTkButton(
            toolbar,
            text=self._tr('history.clear'),
            width=108,
            height=30,
            corner_radius=8,
            fg_color=self.C_BTN,
            hover_color=self.C_BTN_HOV,
            text_color=self._palette['button_text'],
            command=self._clear_history_items,
            font=ctk.CTkFont(size=12),
        ).grid(row=0, column=1, sticky='e')

        self._history_scroll = ctk.CTkScrollableFrame(
            card,
            fg_color='transparent',
            corner_radius=0,
            height=180,
        )
        self._history_scroll.grid(row=2, column=0, padx=8, pady=(0, 10), sticky='ew')
        self._history_scroll.grid_columnconfigure(0, weight=1)
        self._refresh_history_panel()

    def _refresh_history_panel(self):
        if not hasattr(self, '_history_scroll'):
            return
        for widget in self._history_scroll.winfo_children():
            widget.destroy()

        entries = recent_history(50)
        if not entries:
            ctk.CTkLabel(
                self._history_scroll,
                text=self._tr('history.empty'),
                text_color=self._palette['text_subtle'],
                font=ctk.CTkFont(size=12),
                anchor='w',
            ).grid(row=0, column=0, padx=6, pady=6, sticky='w')
            return

        for idx, item in enumerate(entries):
            row = ctk.CTkFrame(
                self._history_scroll,
                corner_radius=8,
                fg_color=self._palette['track_bg'],
                border_width=1,
                border_color=self._palette['card_edge'],
            )
            row.grid(row=idx, column=0, padx=2, pady=2, sticky='ew')
            row.grid_columnconfigure(0, weight=1)

            title = item.get('title') or item.get('url') or self._tr('history.untitled')
            date = item.get('download_date') or ''
            path = item.get('file_path') or ''

            ctk.CTkLabel(
                row,
                text=title,
                anchor='w',
                font=ctk.CTkFont(size=12, weight='bold'),
                text_color=self._palette['text_primary'],
            ).grid(row=0, column=0, padx=(10, 8), pady=(8, 2), sticky='ew')

            ctk.CTkLabel(
                row,
                text=date,
                anchor='w',
                font=ctk.CTkFont(size=11),
                text_color=self._palette['text_subtle'],
            ).grid(row=1, column=0, padx=(10, 8), pady=(0, 8), sticky='w')

            open_btn = ctk.CTkButton(
                row,
                text=self._tr('history.open_folder'),
                width=106,
                height=28,
                corner_radius=7,
                fg_color=self.C_BTN,
                hover_color=self.C_BTN_HOV,
                text_color=self._palette['button_text'],
                font=ctk.CTkFont(size=11),
                command=lambda p=path: self._open_history_item_folder(p),
            )
            open_btn.grid(row=0, column=1, rowspan=2, padx=(0, 8), pady=8)
            if not path:
                open_btn.configure(state='disabled')

    def _open_history_item_folder(self, file_path: str):
        if not file_path:
            return
        folder = file_path if os.path.isdir(file_path) else os.path.dirname(file_path)
        self._open_path(folder)

    def _clear_history_items(self):
        answer = messagebox.askyesno(
            self._tr('history.clear_title'),
            self._tr('history.clear_message'),
        )
        if not answer:
            return
        clear_history()
        self._refresh_history_panel()

    # ─────────────────────────────────────────────
    #  Queue polling
    # ─────────────────────────────────────────────
    def _poll(self):
        if not self.winfo_exists():
            return
        try:
            while True:
                item = self._log_queue.get_nowait()
                kind = item[0]

                if kind == 'progress':
                    pct, speed, eta, sz = item[1]
                    self._prog_bar.set(pct)
                    self._s_pct.configure(text=f'{pct * 100:.1f}%')
                    if speed and speed != '─':
                        self._s_speed.configure(text=f'🚀 {speed}')
                    if eta and eta != '─':
                        self._s_eta.configure(text=f'⏱ {eta}')
                    if sz and sz != '─':
                        self._s_size.configure(text=f'📦 {sz}')

                elif kind == 'track_start':
                    idx, total, title = item[1], item[2], item[3]
                    self._pl_total = total
                    self._show_tracklist(total)
                    if idx in self._track_rows:
                        self._track_rows[idx].set_title(title)
                        self._track_rows[idx].update_status('downloading')
                    self._s_status.configure(
                        text=f'TRACK {idx}/{total}',
                        text_color=self._palette['accent'],
                    )

                elif kind == 'track_pct':
                    idx, pct = item[1], item[2]
                    if idx in self._track_rows:
                        self._track_rows[idx].update_status('downloading', pct)

                elif kind == 'track_done':
                    idx, title, extra = item[1], item[2], item[3]
                    full_path = item[4] if len(item) > 4 else ''
                    if idx in self._track_rows:
                        self._track_rows[idx].set_title(title)
                        self._track_rows[idx].update_status('done', extra=extra)
                    if full_path:
                        self._last_download_path = full_path
                        self._bind_track_open(idx, full_path)

                elif kind == 'track_error':
                    idx = item[1]
                    if idx in self._track_rows:
                        self._track_rows[idx].update_status('error')

                elif kind == 'single_done':
                    title, fn = item[1], item[2]
                    full_path = item[3] if len(item) > 3 else ''
                    self._show_single(title, fn)
                    if full_path:
                        self._last_download_path = full_path
                        self._bind_track_open(1, full_path)

                elif kind == 'preview_data':
                    summary = item[1]
                    self._show_preview_data(summary)

                elif kind == 'preview_error':
                    message = item[1]
                    self._show_preview_error(message)

                elif kind == 'history_refresh':
                    self._refresh_history_panel()

                elif kind == 'update_ytdlp':
                    self._show_ytdlp_update_notice(item[1])

                elif kind == 'update_app':
                    self._show_app_update_notice(item[1], item[2])

                elif kind == 'update_ytdlp_done':
                    ok = bool(item[1])
                    if ok:
                        self._ytdlp_notice_label.configure(text=self._tr('update.ytdlp.done'))
                    else:
                        self._ytdlp_notice_label.configure(text=self._tr('update.ytdlp.failed'))
                    self._ytdlp_notice_btn.configure(state='normal')

                elif kind == 'done':
                    success = item[1]
                    err_msg = item[2] if len(item) > 2 else ''
                    is_cancelled = bool(item[3]) if len(item) > 3 else False
                    self._is_downloading = False
                    self._prog_bar.set(1.0 if success else self._prog_bar.get())
                    tc = self.C_SUCCESS if success else (self.C_ERR if not is_cancelled else self._palette['warning_text'])
                    if success:
                        lbl = self._tr('status.done')
                    elif is_cancelled:
                        lbl = err_msg or self._tr('status.cancelled')
                        self._prog_bar.set(0)
                        self._s_pct.configure(text='0.0%')
                        self._s_speed.configure(text=self._tr('status.idle'))
                        self._s_eta.configure(text=self._tr('status.idle'))
                        self._s_size.configure(text=self._tr('status.idle'))
                    else:
                        lbl = f"✗ {err_msg or self._tr('status.failed')}"
                    self._s_pct.configure(text_color=tc)
                    self._s_status.configure(text=lbl, text_color=tc)
                    if success and self._last_download_path:
                        self._open_folder_btn.configure(text=self._tr('button.open_folder'))
                        self._open_folder_btn.grid()
                    else:
                        self._open_folder_btn.grid_remove()
                    self._dl_btn.configure(
                        text=self._tr('button.download'),
                        fg_color=self.C_RED,
                        hover_color=self.C_RED_HOV,
                    )

        except queue.Empty:
            pass
        self.after(80, self._poll)

    def _q(self, *args):
        self._log_queue.put(args)

    # ─────────────────────────────────────────────
    #  Track listesi yönetimi
    # ─────────────────────────────────────────────
    def _show_tracklist(self, total: int):
        if not self._pl_scroll.winfo_ismapped():
            self._pl_empty.grid_remove()
            self._pl_scroll.grid()

        for i in range(1, total + 1):
            if i not in self._track_rows:
                tr = TrackRow(self._pl_scroll, i, '...', self._palette)
                tr.grid(row=i - 1, column=0, padx=2, pady=2, sticky='ew')
                self._track_rows[i] = tr

    def _show_single(self, title: str, fn: str):
        if not self._pl_scroll.winfo_ismapped():
            self._pl_empty.grid_remove()
            self._pl_scroll.grid()
        if 1 not in self._track_rows:
            tr = TrackRow(self._pl_scroll, 1, title, self._palette)
            tr.grid(row=0, column=0, padx=2, pady=2, sticky='ew')
            self._track_rows[1] = tr
        self._track_rows[1].set_title(title)
        self._track_rows[1].update_status('done', extra=fn)

    # ─────────────────────────────────────────────
    #  Olay işleyicileri
    # ─────────────────────────────────────────────
    def _on_type(self, value: str):
        if value == self._type_video_label:
            self._media_type = 'video'
            self._fmt = self._vfmt_seg.get().lower()
            self._afmt_frame.grid_remove()
            self._vfmt_frame.grid()
            self._a_opts.grid_remove()
            self._v_opts.grid()
        else:
            self._media_type = 'audio'
            self._fmt = self._afmt_seg.get().lower()
            self._vfmt_frame.grid_remove()
            self._afmt_frame.grid()
            self._v_opts.grid_remove()
            self._a_opts.grid()

    def _browse(self):
        from tkinter import filedialog
        folder = filedialog.askdirectory(initialdir=self._download_folder)
        if folder:
            self._download_folder = folder
            self._out_entry.delete(0, 'end')
            self._out_entry.insert(0, folder)

    def _paste(self):
        for fn in (
            lambda: self.clipboard_get(),
            lambda: __import__('pyperclip').paste(),
        ):
            try:
                text = fn()
                if text and text.strip():
                    self._set_url_text(text.strip())
                    return
            except Exception:
                continue

    def _clear_widget_text(self, widget):
        try:
            widget.delete('1.0', 'end')
        except Exception:
            try:
                widget.delete(0, 'end')
            except Exception:
                pass

    def _set_url_text(self, text: str):
        self._clear_widget_text(self.url_entry)
        self.url_entry.insert('1.0', text)

    def _get_url_text(self) -> str:
        try:
            return self.url_entry.get('1.0', 'end').strip()
        except Exception:
            return self.url_entry.get().strip()

    def _clear_url_text(self):
        self._clear_widget_text(self.url_entry)
        if hasattr(self, '_url_summary'):
            self._url_summary.configure(
                text=self._tr('fetch_summary.idle'),
                text_color=self._palette['text_subtle'],
            )
        try:
            self.url_entry.focus_set()
        except Exception:
            pass

    def _open_path(self, path: str):
        if not path:
            return
        try:
            if os.name == 'nt':
                os.startfile(path)
            elif sys.platform == 'darwin':
                subprocess.run(['open', path], check=False)
            else:
                subprocess.run(['xdg-open', path], check=False)
        except Exception:
            pass

    def _open_last_folder(self):
        if not self._last_download_path:
            return
        folder = os.path.dirname(self._last_download_path) or self._download_folder
        self._open_path(folder)

    def _bind_track_open(self, idx: int, path: str):
        row = self._track_rows.get(idx)
        if not row:
            return
        self._track_files[idx] = path

        def _open(_event=None):
            self._open_path(path)

        for widget in (row, row._title, row._info, row._icon):
            widget.bind('<Button-1>', _open)

    def _open_ffmpeg_download(self, _event=None):
        try:
            webbrowser.open(FFMPEG_DOWNLOAD_URL)
        except Exception:
            pass

    def _start_update_checks(self):
        threading.Thread(target=self._update_check_worker, daemon=True).start()

    def _update_check_worker(self):
        try:
            from yt_dlp.version import __version__ as installed_ytdlp_version
        except Exception:
            installed_ytdlp_version = None

        latest_ytdlp = fetch_latest_ytdlp_version()
        if latest_ytdlp and is_newer_version(latest_ytdlp, installed_ytdlp_version):
            self._q('update_ytdlp', latest_ytdlp)

        latest_tag, latest_url = fetch_latest_release(APP_RELEASE_REPO)
        if latest_tag and latest_url and is_newer_version(latest_tag, __version__):
            self._q('update_app', latest_tag, latest_url)

    def _show_ytdlp_update_notice(self, latest_version: str):
        self._latest_ytdlp_version = latest_version
        self._ytdlp_notice_label.configure(
            text=self._tr('update.ytdlp.available', version=latest_version)
        )
        self._ytdlp_notice.grid()
        self._refresh_update_notice_visibility()

    def _show_app_update_notice(self, latest_tag: str, latest_url: str):
        self._latest_app_release_url = latest_url
        self._app_notice_label.configure(
            text=self._tr('update.app.available', version=latest_tag)
        )
        self._app_notice.grid()
        self._refresh_update_notice_visibility()

    def _run_ytdlp_update(self):
        self._ytdlp_notice_btn.configure(state='disabled')
        self._ytdlp_notice_label.configure(text=self._tr('update.ytdlp.running'))
        threading.Thread(target=self._run_ytdlp_update_worker, daemon=True).start()

    def _run_ytdlp_update_worker(self):
        cmd = [sys.executable, '-m', 'pip', 'install', '-U', 'yt-dlp']
        ok = False
        try:
            completed = subprocess.run(
                cmd,
                check=False,
                capture_output=True,
                text=True,
            )
            ok = completed.returncode == 0
        except Exception:
            ok = False
        self._q('update_ytdlp_done', ok)

    def _open_latest_release_page(self):
        if not self._latest_app_release_url:
            return
        try:
            webbrowser.open(self._latest_app_release_url)
        except Exception:
            pass

    # ─────────────────────────────────────────────
    #  İndirme başlat
    # ─────────────────────────────────────────────
    def start_download(self):
        raw = self._get_url_text()
        if not raw:
            return
        urls = [u.strip() for u in raw.splitlines() if u.strip()]
        if not urls:
            return
        valid_count = sum(1 for u in urls if is_valid_download_url(u))
        if valid_count == 0:
            self._s_status.configure(text=self._tr('status.invalid_url'), text_color=self.C_ERR)
            return
        if any(has_url(u) for u in urls):
            proceed = messagebox.askyesno(
                self._tr('dialog.duplicate_title'),
                self._tr('dialog.duplicate_message'),
            )
            if not proceed:
                return
        if not has_internet_connection():
            self._s_status.configure(text=self._tr('status.no_internet'), text_color=self.C_ERR)
            return

        for w in self._pl_scroll.winfo_children():
            w.destroy()
        self._track_rows.clear()
        self._track_files.clear()
        self._current_dl_idx = None
        self._pl_total = 0
        self._last_download_path = ''
        self._pl_scroll.grid_remove()
        self._pl_empty.grid()
        self._open_folder_btn.grid_remove()
        self._batch_total = len(urls)
        self._batch_index = 0
        self._batch_urls = {idx: u for idx, u in enumerate(urls, start=1)}

        self._dl_btn.configure(
            text=self._tr('button.cancel'),
            fg_color=self._palette['warning'],
            hover_color=self._palette['warning_hover'],
        )
        self._is_downloading = True
        self._cancel_event.clear()
        self._prog_bar.set(0)
        self._s_pct.configure(text='0.0%', text_color=self._palette['text_muted'])
        self._s_speed.configure(text=self._tr('status.idle'))
        self._s_eta.configure(text=self._tr('status.idle'))
        self._s_size.configure(text=self._tr('status.idle'))
        self._s_status.configure(text=self._tr('status.idle'), text_color=self._palette['text_muted'])

        threading.Thread(target=self._worker, args=(urls,), daemon=True).start()

    def cancel_download(self):
        if not self._is_downloading:
            return
        self._cancel_event.set()
        self._s_status.configure(text=self._tr('status.cancelling'), text_color=self._palette['warning_text'])

    def _record_history(self, info: dict, filename: str):
        file_path = filename or ''
        source_url = (
            info.get('webpage_url')
            or info.get('original_url')
            or info.get('url')
            or self._batch_urls.get(self._batch_index, '')
        )
        title = info.get('title', '')
        file_size = None
        if file_path and os.path.isfile(file_path):
            try:
                file_size = os.path.getsize(file_path)
            except OSError:
                file_size = None
        append_history({
            'url': source_url,
            'title': title,
            'format_quality': f'{self._media_type}:{self._fmt}',
            'download_date': datetime.now().isoformat(timespec='seconds'),
            'file_path': file_path,
            'file_size': file_size,
        })
        self._q('history_refresh')

    # ─────────────────────────────────────────────
    #  Arka plan worker
    # ─────────────────────────────────────────────
    def _worker(self, urls: list[str]):
        output_dir = self._out_entry.get().strip() or self._download_folder
        fmt = self._fmt

        try:
            import yt_dlp
        except ImportError:
            self._q('done', False, self._tr('error.ytdlp_missing'))
            return

        ydl_opts = {
            'paths':          {'home': output_dir},
            'quiet':          False,
            'no_warnings':    False,
            'progress_hooks': [self._progress_hook],
            'logger':         _Logger(),
            'outtmpl': {
                'default': DEFAULT_OUTTMPL,
            },
            'writethumbnail': False,
            'ignoreerrors':   False,
        }
        if self._ffmpeg_location:
            ydl_opts['ffmpeg_location'] = self._ffmpeg_location

        if self._media_type == 'video':
            self._build_video_opts(ydl_opts, fmt)
        else:
            self._build_audio_opts(ydl_opts, fmt)

        total = len(urls)
        success_count = 0
        had_error = False
        last_error_msg = self._tr('error.download')
        for idx, url in enumerate(urls, start=1):
            if self._cancel_event.is_set():
                self._q('done', False, self._tr('status.cancelled'), True)
                return

            self._batch_index = idx
            self._batch_total = total
            self._q('track_start', idx, total, url)
            if not is_valid_download_url(url):
                had_error = True
                last_error_msg = self._tr('status.invalid_url')
                self._q('track_error', idx)
                continue
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ret = ydl.download([url])
                if ret == 0:
                    success_count += 1
                else:
                    had_error = True
                    last_error_msg = self._tr('error.download')
                    self._q('track_error', idx)
            except yt_dlp.utils.DownloadCancelled:
                self._q('track_error', idx)
                self._q('done', False, self._tr('status.cancelled'), True)
                return
            except Exception as exc:
                had_error = True
                self._q('track_error', idx)
                if self._cancel_event.is_set():
                    self._q('done', False, self._tr('status.cancelled'), True)
                    return
                last_error_msg = self._tr(map_download_exception_key(exc))
                self._q('progress', (0.0, '─', '─', '─'))

        if success_count == total and not had_error:
            self._q('done', True)
        else:
            self._q('done', False, last_error_msg)

    def _build_video_opts(self, opts: dict, fmt: str):
        res    = self._res_var.get()
        vcodec = self._vcodec_var.get()
        fps    = self._fps_var.get()
        hdr    = self._hdr_var.get()

        h = '9999'
        if res != self._tr('opt.best'):
            m = re.search(r'(\d+)p', res)
            if m:
                h = m.group(1)

        vc_map = {
            self._tr('opt.auto'): '',
            'h264 (AVC)':  '[vcodec^=avc]',
            'h265 (HEVC)': '[vcodec^=hev]',
            'VP9':         '[vcodec^=vp9]',
            'AV1':         '[vcodec^=av01]',
        }
        vc    = vc_map.get(vcodec, '')
        hdr_f = (
            '[dynamic_range!=HDR10][dynamic_range!=HLG][dynamic_range!=DV]'
            if hdr == self._tr('opt.hdr_sdr_only') else ''
        )
        fps_f = f'[fps<={fps}]' if fps != self._tr('opt.unlimited') else ''

        opts['format'] = (
            f'bestvideo[height<={h}]{fps_f}{vc}{hdr_f}'
            f'+bestaudio/best[height<={h}]'
        )
        opts['merge_output_format'] = fmt

    def _build_audio_opts(self, opts: dict, fmt: str):
        quality  = self._abitrate_var.get()
        sr       = self._samplerate_var.get()
        channels = self._channels_var.get()

        bitrate = '0' if quality == self._tr('opt.audio_best_vbr') else quality.replace('k', '')

        opts['format']         = 'bestaudio/best'
        opts['postprocessors'] = [{
            'key':              'FFmpegExtractAudio',
            'preferredcodec':   fmt,
            'preferredquality': bitrate,
        }]

        extra: list = []
        if sr != self._tr('opt.auto'):
            extra += ['-ar', sr.replace(' Hz', '')]
        if channels == self._tr('opt.channel_stereo'):
            extra += ['-ac', '2']
        elif channels == self._tr('opt.channel_mono'):
            extra += ['-ac', '1']
        if extra:
            opts['postprocessor_args'] = {'FFmpegExtractAudio': extra}

    def _format_duration(self, seconds: int | float | None) -> str:
        if not isinstance(seconds, (int, float)) or seconds < 0:
            return '-'
        total = int(seconds)
        h, rem = divmod(total, 3600)
        m, s = divmod(rem, 60)
        if h:
            return f'{h}:{m:02d}:{s:02d}'
        return f'{m}:{s:02d}'

    def _build_fetch_summary_text(self, summary: dict[str, object]) -> str:
        duration = self._format_duration(summary.get('duration'))
        title = str(summary.get('title') or '-')
        channel = str(summary.get('channel') or '-')
        channel_label = self._tr('fetch_summary.channel_label')
        if summary.get('is_playlist'):
            return self._tr(
                'fetch_summary.playlist',
                kind=self._tr('fetch_summary.playlist_kind'),
                count=summary.get('count') or 0,
                title=title,
                duration=duration,
                channel_label=channel_label,
                channel=channel,
            )
        return self._tr(
            'fetch_summary.single',
            kind=self._tr('fetch_summary.single_kind'),
            title=title,
            duration=duration,
            channel_label=channel_label,
            channel=channel,
        )

    def _show_preview_data(self, summary: dict[str, object]):
        self._preview_loading = False
        self._url_summary.configure(
            text=self._build_fetch_summary_text(summary),
            text_color=self.C_SUCCESS,
        )

    def _show_preview_error(self, message: str):
        self._preview_loading = False
        self._url_summary.configure(text=message, text_color=self.C_ERR)

    def _preview_worker(self, url: str):
        try:
            import yt_dlp
        except ImportError:
            self._q('preview_error', self._tr('error.ytdlp_missing'))
            return

        opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
        }
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
            self._q('preview_data', summarize_media_info(info, url))
        except Exception as exc:
            self._q('preview_error', self._tr(map_download_exception_key(exc)))

    # ─────────────────────────────────────────────
    #  Progress hook (arka plan thread'inden)
    # ─────────────────────────────────────────────
    def _progress_hook(self, d: dict):
        if self._cancel_event.is_set():
            import yt_dlp

            raise yt_dlp.utils.DownloadCancelled()

        def clean(s: str) -> str:
            return re.sub(r'\x1b\[[0-9;]*m', '', s or '─').strip()

        info  = d.get('info_dict', {})
        idx   = info.get('playlist_index')
        total = info.get('n_entries')
        title = info.get('title', '')
        batch_idx = self._batch_index
        batch_total = self._batch_total

        if d['status'] == 'downloading':
            raw_pct = clean(d.get('_percent_str', '0%'))
            try:
                pct = float(raw_pct.replace('%', '')) / 100
            except ValueError:
                pct = 0.0

            speed = clean(d.get('_speed_str', ''))
            eta   = clean(d.get('_eta_str', ''))
            sz    = clean(d.get(
                '_total_bytes_str',
                d.get('_total_bytes_estimate_str', '─'),
            ))
            self._q('progress', (pct, speed, eta, sz))

            if idx and total:
                if idx != self._current_dl_idx:
                    self._current_dl_idx = idx
                    self._q('track_start', idx, total, title)
                else:
                    self._q('track_pct', idx, pct)
            elif batch_total > 1 and batch_idx:
                self._q('track_pct', batch_idx, pct)

        elif d['status'] == 'finished':
            full_path = d.get('filename', '')
            fn = os.path.basename(full_path)
            try:
                self._record_history(info, full_path)
            except Exception:
                pass
            if idx and total:
                self._q('track_done', idx, title, fn, full_path)
            elif batch_total > 1 and batch_idx:
                self._q('track_done', batch_idx, title or full_path, fn, full_path)
            else:
                self._q('single_done', title, fn, full_path)


# ─────────────────────────────────────────────────
if __name__ == '__main__':
    app = App()
    app.mainloop()
