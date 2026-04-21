# YT Downloader

yt-dlp motoru üzerine inşa edilmiş, kullanımı kolay masaüstü video/ses indirme aracı.

---

## Özellikler

- **Video İndirme** — MP4, WEBM, MKV formatlarında, 240p'den 8K'ya kadar çözünürlük seçimi
- **Ses İndirme** — MP3, OPUS, FLAC, M4A, WAV formatlarında ses çıkarımı
- **Gelişmiş Kontroller** — Video codec, FPS limiti, HDR filtresi, ses bitrate/örnekleme hızı/kanal ayarları
- **Playlist Desteği** — Çoklu indirme listesi ile track bazlı ilerleme izleme
- **Gerçek Zamanlı İlerleme** — Hız, ETA, dosya boyutu ve yüzde gösterimi
- **Tam Ekran Uyumlu** — Her pencere boyutunda düzgün görünüm

---

## Kurulum

### Gereksinimler

- Python 3.10+
- [ffmpeg](https://ffmpeg.org/download.html) (video/ses dönüştürme için)

### Adımlar

```bash
# Repoyu klonla
git clone https://github.com/Kcguner/yt-downloader.git
cd yt-downloader

# Bağımlılıkları kur
pip install -r requirements.txt

# Çalıştır
python gui.py
```

---

## Kullanım

1. URL alanına video veya playlist bağlantısını yapıştır
2. Video veya Ses türünü seç
3. İstediğin formatı ve kalite ayarlarını belirle
4. **İndir** butonuna bas

---

## Teknoloji

| Bileşen | Teknoloji |
|---|---|
| GUI Framework | [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) |
| İndirme Motoru | [yt-dlp](https://github.com/yt-dlp/yt-dlp) |
| Post-Processing | [ffmpeg](https://ffmpeg.org) |

---

## Sorumluluk Reddi

Bu araç yalnızca yasal içeriklerin indirilmesi için tasarlanmıştır. Kullanıcılar telif hakkı yasalarına uymakla yükümlüdür. Geliştirici, aracın kötüye kullanımından sorumlu tutulamaz.

---

## Lisans

[MIT](LICENSE)