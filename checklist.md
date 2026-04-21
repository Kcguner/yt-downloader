# YT Downloader — Yapılacaklar Listesi

> Son güncelleme: 2026-04-21

---

## 1. GitHub Repo Düzenlemeleri

### 1.1 Repo Açıklaması ve Etiketler
- [ ] GitHub repo sayfasında **Description** alanına şunu yaz:
  `yt-dlp tabanlı masaüstü video/ses indirme aracı — CustomTkinter GUI`
- [ ] **Topics** olarak şunları ekle:
  `youtube`, `downloader`, `yt-dlp`, `gui`, `python`, `customtkinter`, `video-downloader`, `audio-downloader`
- [ ] Repo sayfasında **Website** alanını boş bırak veya varsa bir demo linki ekle

### 1.2 Ekran Görüntüsü
- [ ] GUI'yi aç, tam ekran ve normal ekran olmak üzere 2 screenshot al
- [ ] Dosyaları repo kökünde `assets/` klasörüne kaydet (`assets/screenshot-normal.png`, `assets/screenshot-fullscreen.png`)
- [ ] README.md'ye ekran görüntülerini ekle:
  ```markdown
  ## Ekran Görüntüleri
  ![Normal](assets/screenshot-normal.png)
  ![Tam Ekran](assets/screenshot-fullscreen.png)
  ```
- [ ] Commit ve push et

---

## 2. Hata Yönetimi

### 2.1 ffmpeg Kontrolü
- [x] Uygulama açılırken `ffmpeg` kurulu mu kontrol et
- [x] Kurulu değilse üst kısımda sarı bir uyarı bandı göster:
  `⚠ ffmpeg bulunamadı — video/ses dönüştürme çalışmayacak. ffmpeg.org adresinden indirin.`
- [x] Uyarı bandına tıklanınca tarayıcıda ffmpeg indirme sayfasını aç
- [x] Kontrol yöntemi: `shutil.which("ffmpeg")` ile PATH'te arama yap

### 2.2 İndirme Hataları
- [x] Geçersiz URL girildiğinde kullanıcıya kırmızı hata mesajı göster
- [x] Ağ bağlantısı yoksa "İnternet bağlantısı bulunamadı" mesajı göster
- [x] yt-dlp `ImportError` verirse "yt-dlp kurulu değil — pip install yt-dlp" mesajı göster
- [x] Hata mesajlarını progress bar altındaki status label'ında göster
- [x] `_worker` metodundaki `except Exception` bloğunu genişlet, hata türüne göre farklı mesajlar ver:
  - `DownloadError` → "Video indirilemedi — URL'yi kontrol et"
  - `ExtractorError` → "Bu site desteklenmiyor veya video kaldırılmış"
  - `PostProcessingError` → "Dönüştürme hatası — ffmpeg'i kontrol et"
  - Genel hata → "Beklenmeyen hata oluştu"

---

## 3. İndirme İptal Mekanizması

### 3.1 İptal Butonu
- [x] İndirme başladığında "İNDİR" butonunu "İPTAL" olarak değiştir
- [x] İptal'e basıldığında `yt_dlp.YoutubeDL` nesnesini durdur
- [x] Yarım kalan `.part` dosyalarını temizle veya bırak (kullanıcıya sor)
- [x] İptal sonrası progress bar'ı sıfırla ve status'a "İptal edildi" yaz
- [x] Uygulama yöntemi:
  - [x] `threading.Event()` ile iptal sinyali oluştur
  - [x] `progress_hook` içinde her çağrıda event'i kontrol et
  - [x] Event set edilmişse `raise yt_dlp.utils.DownloadCancelled()`

---

## 4. Çoklu URL Desteği

### 4.1 URL Listesi
- [x] URL entry'sini çok satırlı `CTkTextbox`'a çevir veya yan tarafına "+" butonu ekle
- [x] Birden fazla URL girildiğinde sırayla indir
- [x] Her URL için ayrı ilerleme gösterimi yap
- [x] Hatalı URL'leri atla, diğerlerine devam et

### 4.2 Drag & Drop
- [ ] `tkinterdnd2` veya benzer kütüphane ile sürükle-bırak desteği ekle
- [ ] Tarayıcıdan URL sürüklenince otomatik algıla ve entry'ye yapıştır
- [ ] Birden fazla URL sürüklenebilir olsun

---

## 5. İndirme Geçmişi

### 5.1 Geçmiş Kaydı
- [x] İndirilen dosyaları JSON formatında kaydet (`~/.yt-downloader/history.json`)
- [x] Her kayıtta şunlar tutulsun:
  - URL
  - Başlık
  - Format ve kalite
  - İndirme tarihi
  - Dosya yolu
  - Dosya boyutu
- [x] Aynı URL tekrar indirilmeye çalışıldığında uyar: "Bu video daha önce indirildi. Yine de indir?"

### 5.2 Geçmiş Paneli
- [ ] GUI'ye "Geçmiş" sekmesi veya yan panel ekle
- [ ] Son 50 indirmeyi listele
- [ ] Dosya yoluna tıklayınca klasörü aç
- [ ] Geçmişi temizle butonu

---

## 6. exe Paketleme (PyInstaller)

### 6.1 Tek Dosya Executable
- [ ] PyInstaller ile `.exe` oluştur:
  ```bash
  pip install pyinstaller
  pyinstaller --onefile --windowed --name "YT-Downloader" --icon=assets/icon.ico gui.py
  ```
- [ ] Uygulama ikonu tasarla veya bul (`assets/icon.ico`)
- [ ] `.exe` dosyasının boyutunu kontrol et (CustomTkinter + yt-dlp ile ~80-120 MB olabilir)
- [ ] Test: temiz bir Windows makinede `.exe`'yi çalıştır, Python kurulu olmadan çalıştığını doğrula
- [ ] GitHub Releases'a `.exe` dosyasını yükle
- [ ] README'ye indirme bağlantısı ekle:
  ```markdown
  ## Hızlı Kurulum
  [YT-Downloader.exe indir](https://github.com/Kcguner/yt-downloader/releases/latest)
  ```

### 6.2 .spec Dosyası
- [ ] `YT-Downloader.spec` dosyasını repo'ya ekle (tekrarlanabilir build için)
- [ ] Hidden imports listesini kontrol et (yt-dlp extractors lazy-load yapar)
- [ ] `--collect-all yt_dlp` flag'ini ekle
- [ ] ffmpeg'i bundle'a dahil etme — kullanıcı kendisi kursun

---

## 7. Kullanıcı Deneyimi İyileştirmeleri

### 7.1 Tema Desteği
- [x] Ayarlar bölümüne tema seçici ekle: Koyu (varsayılan), Açık, Sistem
- [x] `ctk.set_appearance_mode()` ile geçiş yap
- [x] Seçimi `~/.yt-downloader/config.json` dosyasına kaydet

### 7.2 Video Önizleme
- [ ] URL yapıştırıldıktan sonra "Bilgi Al" butonu veya otomatik bilgi çekme
- [ ] Thumbnail, başlık, süre ve kanal adını URL kartının altında göster
- [ ] `yt_dlp.YoutubeDL({'extract_flat': True}).extract_info(url, download=False)` kullan
- [ ] Bilgi çekerken küçük spinner göster

### 7.3 Dosya Yöneticisi Entegrasyonu
- [x] İndirme tamamlandığında "Klasörü Aç" butonu göster
- [x] Windows: `os.startfile(folder)`, macOS: `subprocess.run(["open", folder])`
- [x] Track listesindeki tamamlanan dosyalara tıklayınca dosyayı aç

### 7.4 Klavye Kısayolları
- [x] `Ctrl+V` → URL yapıştır
- [x] `Ctrl+Enter` → İndirmeyi başlat
- [x] `Escape` → İndirmeyi iptal et
- [x] `Ctrl+L` → URL alanını temizle ve odakla

---

## 8. Çoklu Dil Desteği

### 8.1 i18n Altyapısı
- [x] `locales/` klasörü oluştur
- [x] `locales/tr.json` ve `locales/en.json` dosyaları yaz
- [x] Tüm UI yazılarını sabit string yerine locale dosyasından çek
- [x] Ayarlarda dil seçici ekle
- [x] Varsayılan dil: Türkçe

---

## 9. Otomatik Güncelleme

### 9.1 yt-dlp Güncelleme
- [ ] Uygulama açılırken yt-dlp'nin güncel olup olmadığını kontrol et
- [ ] PyPI'dan en son versiyonu çek ve karşılaştır
- [ ] Güncelleme varsa bildirim göster: "yt-dlp güncellemesi mevcut — Güncelle"
- [ ] Güncelleme butonu: `pip install -U yt-dlp` komutunu arka planda çalıştır

### 9.2 Uygulama Güncelleme
- [ ] GitHub Releases API ile en son sürümü kontrol et
- [ ] Yeni sürüm varsa indirme bağlantısı göster
- [x] Sürüm numarasını `gui.py` içinde `__version__ = "3.1.0"` olarak tanımla

---

## 10. Test ve Kalite

### 10.1 Manuel Testler
- [ ] Tekli video indirme (YouTube, Twitter, Instagram)
- [ ] Playlist indirme (YouTube playlist, 10+ video)
- [ ] Ses çıkarımı (MP3, FLAC)
- [ ] Farklı çözünürlükler (360p, 720p, 1080p, 4K)
- [ ] Tam ekran ve küçük pencere boyutlarında UI kontrolü
- [ ] Sağ tık menüsünün çalıştığını doğrula
- [ ] Geçersiz URL ile hata mesajını kontrol et
- [ ] İnternet bağlantısı kesildiğinde davranışı test et

### 10.2 Otomatik Testler (opsiyonel)
- [x] `pytest` ile temel unit testler yaz
- [ ] `_build_video_opts` ve `_build_audio_opts` fonksiyonlarını test et
- [ ] Format string oluşturma mantığını doğrula
- [ ] GitHub Actions ile CI pipeline kur

---

## Öncelik Sıralaması

| Öncelik | Madde | Neden |
|---|---|---|
| 🔴 Kritik | 2.1 ffmpeg kontrolü | Kullanıcı hatayı anlayamıyor |
| 🔴 Kritik | 2.2 Hata mesajları | UX temel gereksinimi |
| 🔴 Kritik | 1.2 Ekran görüntüsü | Repo profesyonel görünmeli |
| 🟡 Önemli | 3.1 İptal butonu | Uzun indirmelerde zorunlu |
| 🟡 Önemli | 6.1 exe paketleme | Geniş kitleye ulaşmak için |
| 🟡 Önemli | 7.2 Video önizleme | UX kalitesini artırır |
| 🟢 İsteğe bağlı | 4-5-7-8-9 | Zaman buldukça eklenir |
