# yt-dlp — Proje Dokümantasyonu

> Son güncelleme: 2026-04-21

---

## Proje Hakkında

**yt-dlp**, `youtube-dl` projesinin aktif olarak geliştirilen çatalıdır (fork). Python 3.10+ ile çalışır, `pyproject.toml` + `hatch` / `uv` tabanlı modern build sistemi kullanır. 1.000'den fazla siteden video ve ses indirme desteği sunar.

---

## Dizin Yapısı

```
yt-dlp/
├── yt_dlp/                  ← Ana Python paketi
│   ├── __init__.py          ← CLI giriş noktası, main()
│   ├── YoutubeDL.py         ← Çekirdek indirme motoru (~221 KB)
│   ├── options.py           ← CLI argüman tanımları
│   ├── jsinterp.py          ← JavaScript yorumlayıcısı (sig deobfuscation)
│   ├── aes.py               ← AES şifre çözücü
│   ├── cookies.py           ← Tarayıcı cookie okuyucu
│   ├── plugins.py           ← Plugin altyapısı
│   │
│   ├── extractor/           ← Site-bazlı bilgi çıkarıcılar
│   │   ├── common.py        ← InfoExtractor base class (4192 satır)
│   │   ├── youtube/         ← En kapsamlı extractor
│   │   └── ...              ← Her site için ayrı modül
│   │
│   ├── downloader/          ← Protokol işleyicileri
│   │   ├── http.py          ← HTTP/HTTPS
│   │   ├── hls.py           ← HLS (M3U8)
│   │   ├── dash.py          ← MPEG-DASH
│   │   ├── fragment.py      ← Parçalı indirme
│   │   ├── rtmp.py          ← RTMP
│   │   └── external.py      ← aria2c, wget, curl…
│   │
│   ├── postprocessor/       ← FFmpeg tabanlı son işlemler
│   │   ├── ffmpeg.py        ← Ana FFmpeg wrapper
│   │   ├── sponsorblock.py  ← Reklam segmenti tespiti
│   │   ├── modify_chapters.py
│   │   └── embedthumbnail.py
│   │
│   └── networking/          ← Çok katmanlı ağ altyapısı
│       ├── _urllib.py       ← stdlib fallback
│       ├── _requests.py     ← requests backend
│       └── _curlcffi.py     ← TLS parmak izi taklidi (Cloudflare bypass)
│
├── gui.py                   ← CustomTkinter masaüstü GUI (v3.1)
├── yt_dlp_gui_old.py        ← Eski GUI (arşiv)
└── pyproject.toml           ← Build ve bağımlılık tanımları
```

---

## İndirme Akışı

```
 URL Girişi
    ↓
 Extractor Eşleşmesi       _VALID_URL regex → suitable()
    ↓
 Bilgi Çıkarımı             _real_extract → info_dict
    ↓
 Format Seçimi              FormatSorter + kullanıcı tercihleri
    ↓
 İndirme                    HTTP │ HLS │ DASH │ RTMP │ external
    ↓
 Son İşlem                  FFmpeg: dönüştürme, metadata, altyazı…
```

---

## Temel Bileşenler

| Bileşen | Dosya | İşlev |
|---|---|---|
| Ana Motor | `YoutubeDL.py` | İndirme döngüsünün tamamını yönetir |
| Base Extractor | `extractor/common.py` | Tüm extractor'ların türediği temel sınıf |
| YouTube Extractor | `extractor/youtube/` | En karmaşık ve kapsamlı extractor |
| JS Yorumlayıcı | `jsinterp.py` | Signature deobfuscation |
| AES Çözücü | `aes.py` | Şifreli akış çözümü |
| Cookie Okuyucu | `cookies.py` | Chrome / Firefox / Safari cookie desteği |
| GUI | `gui.py` | CustomTkinter masaüstü arayüzü |

---

## Extractor Yapısı

Her extractor `InfoExtractor` base class'ından türer:

```python
class XxxIE(InfoExtractor):
    _VALID_URL = r'https?://xxx\.com/watch/(?P<id>[a-z0-9]+)'
    _NETRC_MACHINE = 'xxx'  # login desteği (opsiyonel)

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        # ... bilgi çıkarımı ...
        return {
            'id': video_id,
            'title': title,
            'formats': [...],
            'thumbnail': ...,
            'description': ...,
        }
```

### info_dict Alanları

| Kategori | Alanlar |
|---|---|
| **Zorunlu** | `id`, `title`, `formats` veya `url` |
| **Format** | `url`, `ext`, `width`, `height`, `fps`, `vcodec`, `acodec`, `tbr`, `abr`, `vbr`, `protocol` |
| **Metadata** | `thumbnail`, `description`, `uploader`, `upload_date`, `duration`, `view_count`, `like_count` |
| **Kategorik** | `series`, `season`, `episode`, `album`, `track`, `artists`, `genres` |
| **Canlı Yayın** | `is_live`, `was_live`, `live_status` |

---

## Downloader Protokolleri

| Modül | Protokol |
|---|---|
| `http.py` | HTTP / HTTPS |
| `hls.py` | HLS (M3U8) |
| `dash.py` | MPEG-DASH |
| `fragment.py` | Parçalı indirme (genel) |
| `rtmp.py` | RTMP akışı |
| `rtsp.py` | RTSP akışı |
| `external.py` | aria2c, wget, curl, axel, httpie |
| `websocket.py` | WebSocket tabanlı |
| `youtube_live_chat.py` | YouTube canlı sohbet |

---

## Post-Processing Zinciri

İndirme tamamlandıktan sonra sırasıyla çalışan işlemciler:

| # | İşlemci | Görev |
|---|---|---|
| 1 | `MetadataParser` | Metadata ayrıştırma ve değiştirme |
| 2 | `SponsorBlock` | Reklam segmentlerini tespit etme |
| 3 | `FFmpegSubtitlesConvertor` | Altyazı format dönüşümü |
| 4 | `FFmpegExtractAudio` | Ses çıkarımı (mp3, opus, flac…) |
| 5 | `FFmpegVideoRemuxer/Convertor` | Video format dönüşümü |
| 6 | `FFmpegEmbedSubtitle` | Altyazıyı videoya gömme |
| 7 | `ModifyChapters` | Bölüm düzenleme / SponsorBlock uygulama |
| 8 | `FFmpegMetadata` | Metadata embed |
| 9 | `EmbedThumbnail` | Kapak görseli gömme |
| 10 | `FFmpegSplitChapters` | Bölümlere göre dosya ayırma |
| 11 | `XAttrMetadata` | Extended attribute yazma |
| 12 | `FFmpegConcat` | Playlist birleştirme |
| 13 | `Exec` | Özel komut çalıştırma |

---

## GUI (v3.1)

CustomTkinter tabanlı masaüstü arayüzü. Arka planda doğrudan `yt-dlp` Python API'sini kullanır (subprocess yok).

**Yetenekler:**
- **Format seçimi:** MP4, WEBM, MKV (video) — MP3, OPUS, FLAC, M4A, WAV (ses)
- **Video kontrolleri:** Çözünürlük, codec, FPS limiti, HDR filtresi
- **Ses kontrolleri:** Bitrate, örnekleme hızı, kanal sayısı
- **Kayıt yeri:** Klasör seçici ile hedef dizin belirleme
- **İlerleme takibi:** Gerçek zamanlı yüzde, hız, ETA ve dosya boyutu gösterimi
- **Playlist desteği:** Çoklu indirme listesi ile track bazlı ilerleme izleme
- **Pano entegrasyonu:** Tek tıkla URL yapıştırma
- **Tam ekran uyumlu:** Dinamik padding ile her pencere boyutunda düzgün görünüm

---

## Ağ Katmanı

Üç HTTP backend, öncelik sırasıyla:

1. **curl-cffi** — TLS parmak izi taklidi ile Cloudflare bypass
2. **requests** — Standart HTTP istemcisi
3. **urllib** — Python stdlib (fallback)

WebSocket desteği `websockets` kütüphanesi üzerinden sağlanır.

---

## Plugin Sistemi

Dışarıdan extractor ve postprocessor ekleme:

```bash
yt-dlp --plugin-dirs /path/to/plugins URL
```

```
my_plugins/
└── yt_dlp_plugins/
    ├── extractor/
    │   └── custom_site.py
    └── postprocessor/
        └── custom_pp.py
```

---

## Bağımlılıklar

### Önerilen

| Paket | Amaç |
|---|---|
| `brotli` / `brotlicffi` | Brotli sıkıştırma desteği |
| `certifi` | SSL sertifika doğrulama |
| `mutagen` | Audio metadata okuma/yazma |
| `pycryptodomex` | AES şifreleme |
| `requests` | HTTP istemcisi |
| `urllib3` | HTTP altyapısı |
| `websockets` | WebSocket desteği |

### Opsiyonel

| Paket | Amaç |
|---|---|
| `curl-cffi` | Cloudflare bypass (TLS taklidi) |
| `secretstorage` | Linux keyring desteği |
| `deno` | Alternatif JS runtime |

### Harici Araçlar

- **ffmpeg** — Post-processing için gerekli
- **aria2c / wget / curl** — Alternatif downloader
- **Node.js / Bun / QuickJS** — JS runtime alternatifleri

---

## Geliştirme

```bash
# Ortam kurulumu
hatch env create
hatch run setup

# CLI olarak çalıştırma
hatch run yt-dlp URL

# Test
hatch run hatch-test:run

# Lint kontrolü
hatch fmt --check
```

---

## Mimari

```
┌──────────────────────────────────────────────┐
│               CLI  /  GUI                    │
│          __init__.py  /  gui.py              │
└───────────────────┬──────────────────────────┘
                    │
┌───────────────────▼──────────────────────────┐
│              YoutubeDL.py                    │
│     Orkestratör — format seçimi,             │
│     dosya yönetimi, hata yönetimi            │
└────────┬─────────────────────┬───────────────┘
         │                     │
┌────────▼────────┐  ┌────────▼────────────────┐
│   Extractor     │  │     Downloader           │
│   (1000+ IE)    │  │  HTTP / HLS / DASH / …   │
└────────┬────────┘  └────────┬────────────────┘
         │                     │
┌────────▼─────────────────────▼───────────────┐
│             PostProcessor                    │
│   FFmpeg: audio / video / metadata / subs    │
└──────────────────────┬───────────────────────┘
                       │
┌──────────────────────▼───────────────────────┐
│            Networking Layer                  │
│     urllib  /  requests  /  curl-cffi         │
└──────────────────────────────────────────────┘
```
