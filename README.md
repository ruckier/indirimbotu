# 🤖 İndirim Takip Botu

Telegram üzerinden ürün fiyatlarını takip eden ve indirim olduğunda bildirim gönderen Python bot.

## ✨ Özellikler

- ✅ **Otomatik Fiyat Takibi**: Belirlenen URL'lerdeki ürün fiyatlarını takip eder
- ✅ **İndirim Bildirimleri**: %5 ve üzeri indirimlerde Telegram'dan bildirim gönderir
- ✅ **Çoklu Site Desteği**: GSStore, Saat&Saat ve generic scraper ile diğer siteler
- ✅ **Infinite Scroll**: Dinamik yükleme yapan sayfaları otomatik scrollar
- ✅ **Stealth Mode**: Bot algılanmasını önlemek için playwright-stealth kullanır
- ✅ **Telegram Bot**: `/ekle`, `/liste`, `/sil` komutları ile kolay yönetim
- ✅ **Web Dashboard**: `index.html` ile ürünleri görüntüleme

## 📁 Dosya Yapısı

```
discount_tracker/
├── tracker.py          # Ana scraper ve fiyat takip motoru
├── run_bot.py         # Telegram bot servisi
├── setup_bot.py       # İlk kurulum için Telegram ayarları
├── index.html         # Web dashboard
├── script.js          # Dashboard JS
├── style.css          # Dashboard CSS
├── urls.txt           # Takip edilecek URL'ler
├── prices.json        # Fiyat geçmişi (otomatik oluşur)
├── config.py          # Telegram ayarları (gitignore'da)
└── requirements.txt   # Python bağımlılıkları
```

## 🚀 Kurulum

### 1. Bağımlılıkları Yükle

```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. Telegram Bot Ayarla

```bash
python setup_bot.py
```

Bu komut:
- Telegram bot token'ınızı alır
- Chat ID'nizi bulur
- `config.py` dosyasını oluşturur

### 3. URL Ekle

`urls.txt` dosyasına takip etmek istediğiniz ürün linklerini ekleyin:

```
https://www.gsstore.org/giyim-erkek/
https://www.saatvesaat.com.tr/erkek-klasik-saat
```

## 🎮 Kullanım

### Tracker'ı Manuel Çalıştır

```bash
python tracker.py
```

Her çalıştırmada:
1. Telegram'dan yeni eklenen linkleri kontrol eder
2. Tüm URL'leri tarar
3. Fiyat değişikliklerini tespit eder
4. İndirim varsa Telegram'dan bildirim gönderir

### Telegram Bot Servisi

```bash
python run_bot.py
```

Bu mod sürekli çalışır ve şu komutları destekler:

- `/start` - Botu başlat
- `/ekle <link>` - Yeni ürün ekle
- `/liste` - Takip edilen ürünleri göster
- `/sil <numara>` - Ürün sil
- `/yardim` - Yardım mesajı

### Web Dashboard

`index.html` dosyasını tarayıcıda açın:

```bash
# Python ile basit HTTP server
python -m http.server 8000
```

Sonra `http://localhost:8000` adresine gidin.

## 🔧 GitHub Actions (Otomatik Çalıştırma)

`.github/workflows/` dizininde tanımlanan workflow sayesinde:
- Her 30 dakikada bir otomatik çalışır
- Fiyat değişikliklerini kontrol eder
- `prices.json` dosyasını günceller ve commit eder

## 🛠️ Desteklenen Siteler

### 1. GSStore (Özel Scraper)
- Liste sayfaları ✅
- Tekil ürün sayfaları ✅
- Infinite scroll ✅

### 2. Saat&Saat (Özel Scraper)
- Liste sayfaları ✅
- Tekil ürün sayfaları ✅
- Magento 2 desteği ✅

### 3. Generic Scraper (Diğer Siteler)
- OG meta tag desteği ✅
- Genel fiyat tespiti ✅
- Fallback mekanizması ✅

## 📊 Nasıl Çalışır?

1. **Scraping**: Playwright ile sayfa açılır, scroll yapılır, ürün bilgileri çekilir
2. **Price Parsing**: Regex ile fiyat metinlerinden sayısal değer çıkarılır
3. **Comparison**: Önceki fiyatlarla karşılaştırılır (`prices.json`)
4. **Notification**: %5+ indirim varsa Telegram'a screenshot ile mesaj gönderilir
5. **Storage**: Yeni fiyatlar JSON dosyasına kaydedilir

## ⚙️ Ayarlar

### tracker.py İçi Ayarlar

```python
URLS_FILE = "urls.txt"           # URL listesi
PRICES_FILE = "prices.json"      # Fiyat veritabanı
CONFIG_FILE = "config.py"        # Telegram ayarları
LAST_UPDATE_FILE = ".last_update_id"  # Telegram update tracker
```

### İndirim Eşiği

`tracker.py` satır 533:
```python
if discount >= 5:  # %5 ve üzeri
```

### Scroll Ayarları

`simulate_human_behavior()` fonksiyonunda:
```python
for i in range(10):  # Max 10 tur scroll
    time.sleep(1)     # Her scroll arası bekleme
```

## 🐛 Hata Giderme

### Import Hatası: config.py bulunamadı
```bash
python setup_bot.py
```

### Playwright Hatası
```bash
playwright install chromium
```

### Fiyat Bulunamadı
- URL'nin doğru olduğundan emin olun
- Sayfanın JavaScript gerektirip gerektirmediğini kontrol edin
- Generic scraper log'larına bakın

### Telegram Mesaj Gönderilmiyor
- `config.py` içindeki token ve chat_id'yi kontrol edin
- Bot'u Telegram'da başlattığınızdan emin olun

## 📝 Örnek Çıktı

```
--- V3.0 FINAL FIX ---
Bot Calisiyor... (Stealth Mode: ON)
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) ...

Siteye Gidiliyor: https://www.gsstore.org/giyim-erkek/
GSSTORE: https://www.gsstore.org/giyim-erkek/
   Sayfa Başlığı: Erkek Giyim | GS Store
   [DEBUG] process_gsstore içinde scroll başlatılıyor...
>>> SCROLL BAŞLIYOR <<<
   Scroll Turu: 1
   Scroll Turu: 2
   ...
>>> SCROLL BİTTİ <<<
   24 adet liste öğesi (kart) inceleniyor...
   -> 24 ürün çekildi.

Kontrol Tamamlandi.
```

## 🔐 Güvenlik

- ⚠️ `config.py` dosyası `.gitignore`'da - asla commit etmeyin!
- ⚠️ Telegram bot token'ınızı kimseyle paylaşmayın
- ✅ GitHub Secrets kullanarak token'ı güvenle saklayın

## 📈 Gelecek Özellikler

- [ ] Fiyat grafikleri
- [ ] Email bildirimleri
- [ ] Daha fazla site desteği
- [ ] Proxy desteği
- [ ] Multi-user support

## 🤝 Katkıda Bulunma

1. Fork edin
2. Feature branch oluşturun (`git checkout -b feature/amazing`)
3. Commit edin (`git commit -m 'Add amazing feature'`)
4. Push edin (`git push origin feature/amazing`)
5. Pull Request açın

## 📜 Lisans

Bu proje kişisel kullanım içindir. Ticari kullanım için izin gereklidir.

## 👨‍💻 Geliştirici

Made with ❤️ by [indirimbotu]

---

**Not**: Bu bot eğitim amaçlıdır. Web scraping yaparken sitenin `robots.txt` ve kullanım şartlarına uyun.
