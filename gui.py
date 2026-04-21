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

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")


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
        self._fn(f"✗ {m}")


# ─────────────────────────────────────────────────
#  Tek track satırı
# ─────────────────────────────────────────────────
class TrackRow(ctk.CTkFrame):
    _ICON  = {"pending": "⏳", "downloading": "⬇", "done": "✓", "error": "✗"}
    _COLOR = {
        "pending":     "#707070",
        "downloading": "#42A5F5",
        "done":        "#66BB6A",
        "error":       "#EF5350",
    }
    _TITLE_COLOR = {
        "pending":     "#888888",
        "downloading": "white",
        "done":        "#b0b0b0",
        "error":       "#EF5350",
    }

    def __init__(self, parent, idx: int, title: str, **kwargs):
        super().__init__(
            parent,
            corner_radius=8,
            fg_color=("#161616", "#161616"),
            border_width=1,
            border_color=("#222222", "#222222"),
            **kwargs,
        )
        self.grid_columnconfigure(2, weight=1)

        # ── Index badge
        badge = ctk.CTkFrame(self, fg_color=("#1c1c1c", "#1c1c1c"), corner_radius=5, width=42, height=28)
        badge.grid(row=0, column=0, padx=(12, 8), pady=11)
        badge.grid_propagate(False)
        ctk.CTkLabel(
            badge,
            text=f"{idx:03d}",
            font=ctk.CTkFont(size=12, family="Consolas"),
            text_color="#666666",
        ).place(relx=0.5, rely=0.5, anchor="center")

        # ── Status icon
        self._icon = ctk.CTkLabel(
            self,
            text="⏳",
            font=ctk.CTkFont(size=16),
            text_color="#707070",
            width=24,
        )
        self._icon.grid(row=0, column=1, padx=(0, 10))

        # ── Title
        short = (title[:65] + "…") if len(title) > 65 else title
        self._title = ctk.CTkLabel(
            self,
            text=short,
            font=ctk.CTkFont(size=14),
            text_color="#888888",
            anchor="w",
        )
        self._title.grid(row=0, column=2, sticky="ew")

        # ── Progress / info
        self._info = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=12, family="Consolas"),
            text_color="#888888",
            width=200,
            anchor="e",
        )
        self._info.grid(row=0, column=3, padx=(10, 16))

    def set_title(self, title: str):
        short = (title[:65] + "…") if len(title) > 65 else title
        self._title.configure(text=short)

    def update_status(self, status: str, pct: float = 0.0, extra: str = ""):
        icon  = self._ICON.get(status, "?")
        color = self._COLOR.get(status, "#707070")
        tc    = self._TITLE_COLOR.get(status, "#888888")

        self._icon.configure(text=icon, text_color=color)
        self._title.configure(text_color=tc)

        if status == "downloading":
            filled = int(pct * 20)
            bar = "█" * filled + "░" * (20 - filled)
            self._info.configure(
                text=f"{pct * 100:5.1f}%  {bar}",
                text_color="#42A5F5",
            )
            self.configure(
                fg_color=("#161c28", "#161c28"),
                border_color=("#1e3050", "#1e3050"),
            )
        elif status == "done":
            self._info.configure(text=extra or "✓", text_color="#4CAF50")
            self.configure(
                fg_color=("#161616", "#161616"),
                border_color=("#222222", "#222222"),
            )
        elif status == "error":
            self._info.configure(text="hata", text_color="#EF5350")
            self.configure(border_color=("#3d1a1a", "#3d1a1a"))
        else:
            self._info.configure(text="")
            self.configure(
                fg_color=("#161616", "#161616"),
                border_color=("#222222", "#222222"),
            )


# ─────────────────────────────────────────────────
#  Ana uygulama
# ─────────────────────────────────────────────────
class App(ctk.CTk):
    # ── Renk paleti ──
    C_RED       = "#C62828"
    C_RED_HOV   = "#E53935"
    C_BTN       = ("#222222", "#222222")
    C_BTN_HOV   = ("#333333", "#333333")
    C_SUCCESS   = "#4CAF50"
    C_ERR       = "#EF5350"
    C_OPT_BG   = ("#1c1c1c", "#1c1c1c")
    C_OPT_BTN  = ("#2a2a2a", "#2a2a2a")
    C_OPT_HOV  = ("#3a3a3a", "#3a3a3a")
    C_OPT_DRP  = ("#181818", "#181818")
    C_CARD_BG  = ("#131313", "#131313")
    C_BORDER   = ("#222222", "#222222")

    # Tam ekranda içerik genişliği
    MAX_W = 1400

    def __init__(self):
        super().__init__()
        self.title("YT Downloader")
        self.geometry("960x880")
        self.minsize(700, 640)
        self.resizable(True, True)
        self.configure(fg_color=("#0d0d0d", "#0d0d0d"))

        self._download_folder = os.path.join(os.path.expanduser("~"), "Downloads")
        self._log_queue: queue.Queue = queue.Queue()
        self._media_type = "video"
        self._fmt = "mp4"
        self._track_rows: dict[int, TrackRow] = {}
        self._current_dl_idx: int | None = None
        self._pl_total = 0

        # ── Centered container — tam ekranda max genişlik sınırlı ──
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._container = ctk.CTkFrame(self, fg_color="transparent")
        self._container.grid(row=0, column=0, sticky="nsew")
        self._container.grid_columnconfigure(0, weight=1)
        for r in range(8):
            self._container.grid_rowconfigure(r, weight=(1 if r == 7 else 0))

        self.bind("<Configure>", self._on_resize)

        self._build_all()
        self._poll()

    def _on_resize(self, event=None):
        """Tam ekranda container'ı ortala ve max genişliği sınırla."""
        w = self.winfo_width()
        if w > self.MAX_W + 80:
            pad_x = (w - self.MAX_W) // 2
        else:
            pad_x = 24
        self._container.grid_configure(padx=pad_x)

    # ─────────────────────────────────────────────
    #  UI Yardımcıları
    # ─────────────────────────────────────────────
    def _card(self, row: int, title: str = "", expand: bool = False) -> ctk.CTkFrame:
        card = ctk.CTkFrame(
            self._container,
            corner_radius=12,
            fg_color=self.C_CARD_BG,
            border_width=1,
            border_color=self.C_BORDER,
        )
        card.grid(
            row=row, column=0,
            padx=0, pady=(3, 3),
            sticky="nsew" if expand else "ew",
        )
        card.grid_columnconfigure(0, weight=1)
        if expand:
            card.grid_rowconfigure(1, weight=1)
        if title:
            ctk.CTkLabel(
                card, text=title,
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color="#808080",
            ).grid(row=0, column=0, padx=18, pady=(12, 2), sticky="w")
        return card

    def _omenu(self, parent, values, var, **gkw) -> ctk.CTkOptionMenu:
        m = ctk.CTkOptionMenu(
            parent, values=values, variable=var,
            height=38, corner_radius=8,
            fg_color=self.C_OPT_BG,
            button_color=self.C_OPT_BTN,
            button_hover_color=self.C_OPT_HOV,
            dropdown_fg_color=self.C_OPT_DRP,
            text_color=("#d0d0d0", "#d0d0d0"),
            font=ctk.CTkFont(size=13),
        )
        m.grid(**gkw)
        return m

    # ─────────────────────────────────────────────
    #  Sağ tık context menüsü
    # ─────────────────────────────────────────────
    def _bind_context_menu(self, entry: ctk.CTkEntry):
        """Entry widget'ına sağ tık menüsü bağla."""
        inner = entry._entry  # CTkEntry'nin iç tk.Entry'si
        inner.bind("<Button-3>", lambda e: self._show_context_menu(e, entry))

    def _show_context_menu(self, event, entry: ctk.CTkEntry):
        inner = entry._entry
        menu = tk.Menu(
            self, tearoff=0,
            bg="#1c1c1c", fg="#d0d0d0",
            activebackground="#333333", activeforeground="white",
            font=("Segoe UI", 10),
            relief="flat", bd=1,
        )
        menu.add_command(
            label="  Kes",
            command=lambda: self._ctx_cut(inner),
        )
        menu.add_command(
            label="  Kopyala",
            command=lambda: self._ctx_copy(inner),
        )
        menu.add_command(
            label="  Yapıştır",
            command=lambda: self._ctx_paste(entry),
        )
        menu.add_separator()
        menu.add_command(
            label="  Tümünü Seç",
            command=lambda: self._ctx_select_all(inner),
        )
        menu.add_separator()
        menu.add_command(
            label="  Temizle",
            command=lambda: entry.delete(0, "end"),
        )
        menu.tk_popup(event.x_root, event.y_root)

    def _ctx_cut(self, inner):
        if inner.selection_present():
            inner.event_generate("<<Cut>>")

    def _ctx_copy(self, inner):
        if inner.selection_present():
            inner.event_generate("<<Copy>>")

    def _ctx_paste(self, entry: ctk.CTkEntry):
        try:
            text = self.clipboard_get()
            if text:
                # Seçili metin varsa önce sil
                inner = entry._entry
                if inner.selection_present():
                    inner.delete("sel.first", "sel.last")
                entry.insert("insert", text.strip())
        except Exception:
            pass

    def _ctx_select_all(self, inner):
        inner.select_range(0, "end")
        inner.icursor("end")

    # ─────────────────────────────────────────────
    #  Bölüm inşaları
    # ─────────────────────────────────────────────
    def _build_all(self):
        self._build_header()
        self._build_url()
        self._build_type_format()
        self._build_options()
        self._build_save_path()
        self._build_dl_button()
        self._build_progress()
        self._build_tracklist()

    # ── Başlık ──────────────────────────────────
    def _build_header(self):
        hf = ctk.CTkFrame(self._container, fg_color="transparent")
        hf.grid(row=0, column=0, padx=4, pady=(22, 8), sticky="ew")
        hf.grid_columnconfigure(0, weight=1)

        title_frame = ctk.CTkFrame(hf, fg_color="transparent")
        title_frame.grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            title_frame, text="YT",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color="#E53935",
        ).pack(side="left")

        ctk.CTkLabel(
            title_frame, text=" Downloader",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color="#e0e0e0",
        ).pack(side="left")

        info_frame = ctk.CTkFrame(hf, fg_color="transparent")
        info_frame.grid(row=0, column=1, sticky="e")

        ctk.CTkLabel(
            info_frame, text="v3.1",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#606060",
        ).pack(side="left", padx=(0, 8))

        ctk.CTkLabel(
            info_frame, text="•",
            font=ctk.CTkFont(size=13),
            text_color="#505050",
        ).pack(side="left", padx=(0, 8))

        ctk.CTkLabel(
            info_frame, text="yt-dlp engine",
            font=ctk.CTkFont(size=13),
            text_color="#606060",
        ).pack(side="left")

    # ── URL ─────────────────────────────────────
    def _build_url(self):
        card = self._card(1)
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.grid(row=0, column=0, padx=16, pady=16, sticky="ew")
        inner.grid_columnconfigure(0, weight=1)

        # Label
        ctk.CTkLabel(
            inner, text="BAĞLANTI",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#808080",
        ).grid(row=0, column=0, sticky="w", pady=(0, 8), columnspan=2)

        row = ctk.CTkFrame(inner, fg_color="transparent")
        row.grid(row=1, column=0, sticky="ew", columnspan=2)
        row.grid_columnconfigure(0, weight=1)

        self.url_entry = ctk.CTkEntry(
            row,
            placeholder_text="youtube.com/watch?v=... veya playlist bağlantısı yapıştır",
            height=46,
            font=ctk.CTkFont(size=14),
            corner_radius=8,
            border_width=1,
            border_color=("#252525", "#252525"),
            placeholder_text_color="#505050",
        )
        self.url_entry.grid(row=0, column=0, sticky="ew")
        self.url_entry.bind("<Return>", lambda _: self.start_download())
        self._bind_context_menu(self.url_entry)

        btns = ctk.CTkFrame(row, fg_color="transparent")
        btns.grid(row=0, column=1, padx=(8, 0))

        ctk.CTkButton(
            btns, text="Yapıştır", width=90, height=46,
            command=self._paste, corner_radius=8,
            fg_color=self.C_BTN, hover_color=self.C_BTN_HOV,
            font=ctk.CTkFont(size=14),
            text_color="#c0c0c0",
        ).pack(side="left", padx=(0, 5))

        ctk.CTkButton(
            btns, text="✕", width=46, height=46,
            command=lambda: self.url_entry.delete(0, "end"),
            corner_radius=8,
            fg_color=self.C_BTN, hover_color=("#3d1a1a", "#3d1a1a"),
            font=ctk.CTkFont(size=16),
            text_color="#c0c0c0",
        ).pack(side="left")

    # ── Tür + Format (tek kart) ──────────────────
    def _build_type_format(self):
        card = self._card(2)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.grid(row=0, column=0, padx=16, pady=16, sticky="ew")
        inner.grid_columnconfigure(1, weight=1)

        # Tür
        ctk.CTkLabel(
            inner, text="TÜR",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#909090", width=60,
        ).grid(row=0, column=0, sticky="w", padx=(0, 14))

        self._type_seg = ctk.CTkSegmentedButton(
            inner,
            values=["🎬  Video", "🎵  Ses"],
            command=self._on_type,
            font=ctk.CTkFont(size=14),
            height=40,
            corner_radius=8,
        )
        self._type_seg.set("🎬  Video")
        self._type_seg.grid(row=0, column=1, sticky="ew")

        # Separator
        sep = ctk.CTkFrame(inner, fg_color=("#1e1e1e", "#1e1e1e"), height=1)
        sep.grid(row=1, column=0, columnspan=2, sticky="ew", pady=14)

        # Format
        ctk.CTkLabel(
            inner, text="FORMAT",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#909090", width=60,
        ).grid(row=2, column=0, sticky="w", padx=(0, 14))

        # Video formatları
        self._vfmt_frame = ctk.CTkFrame(inner, fg_color="transparent")
        self._vfmt_frame.grid(row=2, column=1, sticky="ew")
        self._vfmt_seg = ctk.CTkSegmentedButton(
            self._vfmt_frame,
            values=["MP4", "WEBM", "MKV"],
            command=lambda v: setattr(self, "_fmt", v.lower()),
            font=ctk.CTkFont(size=14), height=38,
            corner_radius=8,
        )
        self._vfmt_seg.set("MP4")
        self._vfmt_seg.pack(fill="x")

        # Ses formatları
        self._afmt_frame = ctk.CTkFrame(inner, fg_color="transparent")
        self._afmt_frame.grid(row=2, column=1, sticky="ew")
        self._afmt_seg = ctk.CTkSegmentedButton(
            self._afmt_frame,
            values=["MP3", "OPUS", "FLAC", "M4A", "WAV"],
            command=lambda v: setattr(self, "_fmt", v.lower()),
            font=ctk.CTkFont(size=14), height=38,
            corner_radius=8,
        )
        self._afmt_seg.set("MP3")
        self._afmt_seg.pack(fill="x")
        self._afmt_frame.grid_remove()

    # ── Ayarlar ──────────────────────────────────
    def _build_options(self):
        card = self._card(3, "AYARLAR")

        # ── Video ayarları
        self._v_opts = ctk.CTkFrame(card, fg_color="transparent")
        self._v_opts.grid(row=1, column=0, padx=16, pady=(4, 16), sticky="ew")
        for c in range(4):
            self._v_opts.grid_columnconfigure(c, weight=1)

        self._res_var    = ctk.StringVar(value="En İyi")
        self._vcodec_var = ctk.StringVar(value="Otomatik")
        self._fps_var    = ctk.StringVar(value="Sınırsız")
        self._hdr_var    = ctk.StringVar(value="Dahil Et")

        v_fields = [
            ("Çözünürlük",
             ["En İyi", "4320p (8K)", "2160p (4K)", "1440p (2K)",
              "1080p", "720p", "480p", "360p", "240p"],
             self._res_var),
            ("Video Codec",
             ["Otomatik", "h264 (AVC)", "h265 (HEVC)", "VP9", "AV1"],
             self._vcodec_var),
            ("Maks FPS",
             ["Sınırsız", "60", "30", "24"],
             self._fps_var),
            ("HDR",
             ["Dahil Et", "Yalnız SDR"],
             self._hdr_var),
        ]
        for col, (lbl, vals, var) in enumerate(v_fields):
            px = (0 if col == 0 else 8, 0)
            ctk.CTkLabel(
                self._v_opts, text=lbl,
                font=ctk.CTkFont(size=12), text_color="#909090",
            ).grid(row=0, column=col, padx=px, sticky="w", pady=(0, 6))
            self._omenu(self._v_opts, vals, var,
                        row=1, column=col, padx=px, sticky="ew")

        # ── Ses ayarları
        self._a_opts = ctk.CTkFrame(card, fg_color="transparent")
        self._a_opts.grid(row=1, column=0, padx=16, pady=(4, 16), sticky="ew")
        for c in range(3):
            self._a_opts.grid_columnconfigure(c, weight=1)

        self._abitrate_var   = ctk.StringVar(value="En İyi (VBR)")
        self._samplerate_var = ctk.StringVar(value="Otomatik")
        self._channels_var   = ctk.StringVar(value="Otomatik")

        a_fields = [
            ("Kalite / Bitrate",
             ["En İyi (VBR)", "320k", "256k", "192k", "128k", "96k", "64k"],
             self._abitrate_var),
            ("Örnekleme Hızı",
             ["Otomatik", "48000 Hz", "44100 Hz", "22050 Hz"],
             self._samplerate_var),
            ("Kanal",
             ["Otomatik", "Stereo (2)", "Mono (1)"],
             self._channels_var),
        ]
        for col, (lbl, vals, var) in enumerate(a_fields):
            px = (0 if col == 0 else 8, 0)
            ctk.CTkLabel(
                self._a_opts, text=lbl,
                font=ctk.CTkFont(size=12), text_color="#909090",
            ).grid(row=0, column=col, padx=px, sticky="w", pady=(0, 6))
            self._omenu(self._a_opts, vals, var,
                        row=1, column=col, padx=px, sticky="ew")

        self._a_opts.grid_remove()

    # ── Kayıt Yeri ───────────────────────────────
    def _build_save_path(self):
        card = self._card(4, "KAYIT YERİ")
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.grid(row=1, column=0, padx=16, pady=(4, 16), sticky="ew")
        row.grid_columnconfigure(0, weight=1)

        self._out_entry = ctk.CTkEntry(
            row, height=40,
            font=ctk.CTkFont(size=13),
            corner_radius=8,
            border_width=1,
            border_color=("#252525", "#252525"),
            text_color="#c0c0c0",
        )
        self._out_entry.insert(0, self._download_folder)
        self._out_entry.grid(row=0, column=0, sticky="ew")
        self._bind_context_menu(self._out_entry)

        ctk.CTkButton(
            row, text="Gözat", width=84, height=40,
            command=self._browse, corner_radius=8,
            fg_color=self.C_BTN, hover_color=self.C_BTN_HOV,
            font=ctk.CTkFont(size=13),
            text_color="#c0c0c0",
        ).grid(row=0, column=1, padx=(8, 0))

    # ── İndir Butonu ─────────────────────────────
    def _build_dl_button(self):
        self._dl_btn = ctk.CTkButton(
            self._container,
            text="⬇  İNDİR",
            height=54,
            font=ctk.CTkFont(size=18, weight="bold"),
            command=self.start_download,
            fg_color=self.C_RED,
            hover_color=self.C_RED_HOV,
            corner_radius=10,
            text_color="white",
        )
        self._dl_btn.grid(row=5, column=0, padx=0, pady=(8, 4), sticky="ew")

    # ── İlerleme ─────────────────────────────────
    def _build_progress(self):
        card = self._card(6)

        prog_container = ctk.CTkFrame(card, fg_color="transparent")
        prog_container.grid(row=0, column=0, padx=16, pady=(14, 4), sticky="ew")
        prog_container.grid_columnconfigure(0, weight=1)

        self._prog_bar = ctk.CTkProgressBar(
            prog_container, height=12, corner_radius=6,
            progress_color=("#E53935", "#E53935"),
        )
        self._prog_bar.grid(row=0, column=0, sticky="ew")
        self._prog_bar.set(0)

        stats = ctk.CTkFrame(card, fg_color="transparent")
        stats.grid(row=1, column=0, padx=16, pady=(6, 12), sticky="ew")
        stats.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)

        def sl(text="─", bold=False):
            return ctk.CTkLabel(
                stats, text=text,
                font=ctk.CTkFont(size=14, weight="bold" if bold else "normal"),
                text_color="#909090",
            )

        self._s_pct    = sl("0.0%", bold=True)
        self._s_speed  = sl()
        self._s_eta    = sl()
        self._s_size   = sl()
        self._s_status = sl()

        self._s_pct.grid(row=0, column=0, sticky="w")
        self._s_speed.grid(row=0, column=1)
        self._s_eta.grid(row=0, column=2)
        self._s_size.grid(row=0, column=3)
        self._s_status.grid(row=0, column=4, sticky="e")

    # ── Track Listesi ────────────────────────────
    def _build_tracklist(self):
        card = self._card(7, "İNDİRME LİSTESİ", expand=True)

        # Boş durum
        self._pl_empty = ctk.CTkFrame(card, fg_color="transparent")
        self._pl_empty.grid(row=1, column=0, pady=40, sticky="ew")

        ctk.CTkLabel(
            self._pl_empty,
            text="⬇",
            font=ctk.CTkFont(size=32),
            text_color="#404040",
        ).pack(pady=(0, 8))

        ctk.CTkLabel(
            self._pl_empty,
            text="Henüz indirme yok",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color="#606060",
        ).pack()

        ctk.CTkLabel(
            self._pl_empty,
            text="URL gir ve İndir butonuna bas — liste buraya gelecek",
            font=ctk.CTkFont(size=13),
            text_color="#484848",
        ).pack(pady=(4, 0))

        # Scrollable liste
        self._pl_scroll = ctk.CTkScrollableFrame(
            card,
            fg_color="transparent",
            corner_radius=0,
        )
        self._pl_scroll.grid_columnconfigure(0, weight=1)
        self._pl_scroll.grid(
            row=1, column=0, padx=8, pady=(0, 10), sticky="nsew"
        )
        self._pl_scroll.grid_remove()

    # ─────────────────────────────────────────────
    #  Queue polling
    # ─────────────────────────────────────────────
    def _poll(self):
        try:
            while True:
                item = self._log_queue.get_nowait()
                kind = item[0]

                if kind == "progress":
                    pct, speed, eta, sz = item[1]
                    self._prog_bar.set(pct)
                    self._s_pct.configure(text=f"{pct * 100:.1f}%")
                    if speed and speed != "─":
                        self._s_speed.configure(text=f"🚀 {speed}")
                    if eta and eta != "─":
                        self._s_eta.configure(text=f"⏱ {eta}")
                    if sz and sz != "─":
                        self._s_size.configure(text=f"📦 {sz}")

                elif kind == "track_start":
                    idx, total, title = item[1], item[2], item[3]
                    self._pl_total = total
                    self._show_tracklist(total)
                    if idx in self._track_rows:
                        self._track_rows[idx].set_title(title)
                        self._track_rows[idx].update_status("downloading")
                    self._s_status.configure(
                        text=f"📋 {idx} / {total}",
                        text_color="#42A5F5",
                    )

                elif kind == "track_pct":
                    idx, pct = item[1], item[2]
                    if idx in self._track_rows:
                        self._track_rows[idx].update_status("downloading", pct)

                elif kind == "track_done":
                    idx, title, extra = item[1], item[2], item[3]
                    if idx in self._track_rows:
                        self._track_rows[idx].set_title(title)
                        self._track_rows[idx].update_status("done", extra=extra)

                elif kind == "track_error":
                    idx = item[1]
                    if idx in self._track_rows:
                        self._track_rows[idx].update_status("error")

                elif kind == "single_done":
                    title, fn = item[1], item[2]
                    self._show_single(title, fn)

                elif kind == "done":
                    success = item[1]
                    self._prog_bar.set(1.0 if success else self._prog_bar.get())
                    tc = self.C_SUCCESS if success else self.C_ERR
                    lbl = "✓ Tamamlandı" if success else "✗ Başarısız"
                    self._s_pct.configure(text_color=tc)
                    self._s_status.configure(text=lbl, text_color=tc)
                    self._dl_btn.configure(
                        state="normal",
                        text="⬇  İNDİR",
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
                tr = TrackRow(self._pl_scroll, i, "...")
                tr.grid(row=i - 1, column=0, padx=2, pady=2, sticky="ew")
                self._track_rows[i] = tr

    def _show_single(self, title: str, fn: str):
        if not self._pl_scroll.winfo_ismapped():
            self._pl_empty.grid_remove()
            self._pl_scroll.grid()
        if 1 not in self._track_rows:
            tr = TrackRow(self._pl_scroll, 1, title)
            tr.grid(row=0, column=0, padx=2, pady=2, sticky="ew")
            self._track_rows[1] = tr
        self._track_rows[1].set_title(title)
        self._track_rows[1].update_status("done", extra=fn)

    # ─────────────────────────────────────────────
    #  Olay işleyicileri
    # ─────────────────────────────────────────────
    def _on_type(self, value: str):
        if "Video" in value:
            self._media_type = "video"
            self._fmt = self._vfmt_seg.get().lower()
            self._afmt_frame.grid_remove()
            self._vfmt_frame.grid()
            self._a_opts.grid_remove()
            self._v_opts.grid()
        else:
            self._media_type = "audio"
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
            self._out_entry.delete(0, "end")
            self._out_entry.insert(0, folder)

    def _paste(self):
        for fn in (
            lambda: self.clipboard_get(),
            lambda: __import__("pyperclip").paste(),
        ):
            try:
                text = fn()
                if text and text.strip():
                    self.url_entry.delete(0, "end")
                    self.url_entry.insert(0, text.strip())
                    return
            except Exception:
                continue

    # ─────────────────────────────────────────────
    #  İndirme başlat
    # ─────────────────────────────────────────────
    def start_download(self):
        url = self.url_entry.get().strip()
        if not url:
            return

        for w in self._pl_scroll.winfo_children():
            w.destroy()
        self._track_rows.clear()
        self._current_dl_idx = None
        self._pl_total = 0
        self._pl_scroll.grid_remove()
        self._pl_empty.grid()

        self._dl_btn.configure(
            state="disabled",
            text="⏳  İndiriliyor...",
            fg_color="#4a0e0e",
        )
        self._prog_bar.set(0)
        self._s_pct.configure(text="0.0%", text_color="#909090")
        self._s_speed.configure(text="─")
        self._s_eta.configure(text="─")
        self._s_size.configure(text="─")
        self._s_status.configure(text="─", text_color="#909090")

        threading.Thread(target=self._worker, args=(url,), daemon=True).start()

    # ─────────────────────────────────────────────
    #  Arka plan worker
    # ─────────────────────────────────────────────
    def _worker(self, url: str):
        output_dir = self._out_entry.get().strip() or self._download_folder
        fmt = self._fmt

        try:
            import yt_dlp
        except ImportError:
            self._q("done", False)
            return

        ydl_opts = {
            "paths":          {"home": output_dir},
            "quiet":          False,
            "no_warnings":    False,
            "progress_hooks": [self._progress_hook],
            "logger":         _Logger(),
            "outtmpl": {
                "default": "%(playlist_index|)s%(playlist_index& - |)s%(title)s.%(ext)s",
            },
            "writethumbnail": False,
            "ignoreerrors":   True,
        }

        if self._media_type == "video":
            self._build_video_opts(ydl_opts, fmt)
        else:
            self._build_audio_opts(ydl_opts, fmt)

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ret = ydl.download([url])
            self._q("done", ret == 0)
        except Exception:
            self._q("done", False)

    def _build_video_opts(self, opts: dict, fmt: str):
        res    = self._res_var.get()
        vcodec = self._vcodec_var.get()
        fps    = self._fps_var.get()
        hdr    = self._hdr_var.get()

        h = "9999"
        if res != "En İyi":
            m = re.search(r"(\d+)p", res)
            if m:
                h = m.group(1)

        vc_map = {
            "Otomatik":    "",
            "h264 (AVC)":  "[vcodec^=avc]",
            "h265 (HEVC)": "[vcodec^=hev]",
            "VP9":         "[vcodec^=vp9]",
            "AV1":         "[vcodec^=av01]",
        }
        vc    = vc_map.get(vcodec, "")
        hdr_f = (
            "[dynamic_range!=HDR10][dynamic_range!=HLG][dynamic_range!=DV]"
            if hdr == "Yalnız SDR" else ""
        )
        fps_f = f"[fps<={fps}]" if fps != "Sınırsız" else ""

        opts["format"] = (
            f"bestvideo[height<={h}]{fps_f}{vc}{hdr_f}"
            f"+bestaudio/best[height<={h}]"
        )
        opts["merge_output_format"] = fmt

    def _build_audio_opts(self, opts: dict, fmt: str):
        quality  = self._abitrate_var.get()
        sr       = self._samplerate_var.get()
        channels = self._channels_var.get()

        bitrate = "0" if quality == "En İyi (VBR)" else quality.replace("k", "")

        opts["format"]         = "bestaudio/best"
        opts["postprocessors"] = [{
            "key":              "FFmpegExtractAudio",
            "preferredcodec":   fmt,
            "preferredquality": bitrate,
        }]

        extra: list = []
        if sr != "Otomatik":
            extra += ["-ar", sr.replace(" Hz", "")]
        if channels == "Stereo (2)":
            extra += ["-ac", "2"]
        elif channels == "Mono (1)":
            extra += ["-ac", "1"]
        if extra:
            opts["postprocessor_args"] = {"FFmpegExtractAudio": extra}

    # ─────────────────────────────────────────────
    #  Progress hook (arka plan thread'inden)
    # ─────────────────────────────────────────────
    def _progress_hook(self, d: dict):
        def clean(s: str) -> str:
            return re.sub(r"\x1b\[[0-9;]*m", "", s or "─").strip()

        info  = d.get("info_dict", {})
        idx   = info.get("playlist_index")
        total = info.get("n_entries")
        title = info.get("title", "")

        if d["status"] == "downloading":
            raw_pct = clean(d.get("_percent_str", "0%"))
            try:
                pct = float(raw_pct.replace("%", "")) / 100
            except ValueError:
                pct = 0.0

            speed = clean(d.get("_speed_str", ""))
            eta   = clean(d.get("_eta_str", ""))
            sz    = clean(d.get(
                "_total_bytes_str",
                d.get("_total_bytes_estimate_str", "─"),
            ))
            self._q("progress", (pct, speed, eta, sz))

            if idx and total:
                if idx != self._current_dl_idx:
                    self._current_dl_idx = idx
                    self._q("track_start", idx, total, title)
                else:
                    self._q("track_pct", idx, pct)

        elif d["status"] == "finished":
            fn = os.path.basename(d.get("filename", ""))
            if idx and total:
                self._q("track_done", idx, title, fn)
            else:
                self._q("single_done", title, fn)


# ─────────────────────────────────────────────────
if __name__ == "__main__":
    app = App()
    app.mainloop()