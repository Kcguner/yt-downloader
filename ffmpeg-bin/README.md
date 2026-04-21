# ffmpeg binaries

PyInstaller build sırasında gömülü ffmpeg kullanmak için bu klasöre aşağıdaki dosyaları koyun:

- `ffmpeg.exe`
- `ffprobe.exe`

Linux/macOS build için aynı isimlerin uzantısız sürümleri de desteklenir:

- `ffmpeg`
- `ffprobe`

`YTDownloader.spec` ve `YouTubeDownloader.spec` dosyaları bu klasörü otomatik tarar ve varsa binary'leri `ffmpeg-bin` olarak pakete ekler.
