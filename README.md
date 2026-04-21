# YT Downloader

[TR](#tr) | [EN](#en)

---

## TR

yt-dlp motoru üzerine inşa edilmiş, kullanımı kolay masaüstü video/ses indirme aracı.

### Özellikler

- Video indirme: MP4, WEBM, MKV; 240p–8K çözünürlük seçimi
- Ses indirme: MP3, OPUS, FLAC, M4A, WAV
- Gelişmiş kontroller: Video codec, FPS limiti, HDR filtresi, ses bitrate/örnekleme/kanal
- Playlist desteği: Track bazlı ilerleme
- Gerçek zamanlı ilerleme: Hız, ETA, dosya boyutu, yüzde
- Tam ekran uyumlu arayüz
- Dil desteği: Türkçe / English

### Kurulum

Gereksinimler:

- Python 3.10+
- ffmpeg (kaynak koddan çalıştırırken PATH'te olmalı; `.exe` paketinde gömülü gelir)

```bash
git clone https://github.com/Kcguner/yt-downloader.git
cd yt-downloader
pip install -r requirements.txt
python gui.py
```

`.exe` build (gömülü ffmpeg):

- PyInstaller öncesi `ffmpeg-bin/` klasörüne `ffmpeg.exe` ve `ffprobe.exe` koy
- `.spec` dosyaları bu dosyaları otomatik pakete ekler

### Kullanım

1. URL alanına video veya playlist bağlantısını yapıştır
2. Video/Ses türünü seç
3. Format ve kalite ayarlarını belirle
4. `İndir` butonuna bas

### Teknoloji

| Bileşen | Teknoloji |
|---|---|
| GUI Framework | [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) |
| İndirme Motoru | [yt-dlp](https://github.com/yt-dlp/yt-dlp) |
| Post-Processing | [ffmpeg](https://ffmpeg.org) |

### Sorumluluk Reddi

Bu araç yalnızca yasal içeriklerin indirilmesi için tasarlanmıştır. Kullanıcılar telif hakkı yasalarına uymakla yükümlüdür.

---

## EN

Desktop video/audio downloader powered by yt-dlp.

### Features

- Video download: MP4, WEBM, MKV; 240p–8K resolution selection
- Audio extraction: MP3, OPUS, FLAC, M4A, WAV
- Advanced controls: Video codec, FPS cap, HDR filter, audio bitrate/sample rate/channels
- Playlist support with per-track progress
- Real-time progress: Speed, ETA, file size, percentage
- Fullscreen-friendly UI
- Language support: Turkish / English

### Setup

Requirements:

- Python 3.10+
- ffmpeg (must be on PATH when running from source; bundled in `.exe` builds)

```bash
git clone https://github.com/Kcguner/yt-downloader.git
cd yt-downloader
pip install -r requirements.txt
python gui.py
```

`.exe` build (bundled ffmpeg):

- Put `ffmpeg.exe` and `ffprobe.exe` under `ffmpeg-bin/` before PyInstaller
- `.spec` files auto-include these binaries in the package

### Usage

1. Paste a video or playlist URL
2. Select Video or Audio
3. Choose format and quality
4. Click `Download`

### Disclaimer

This tool is intended for downloading legal content only. Users are responsible for complying with copyright laws.

---

## License

[MIT](LICENSE)
