import logging
import os
import sys
import time
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

# Config import
try:
    import config
except ImportError:
    print("HATA: config.py bulunamadı! Önce setup_bot.py'yi çalıştırın.")
    sys.exit(1)

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

URLS_FILE = "urls.txt"

# --- Komutlar ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bot'u başlat"""
    await update.message.reply_text(
        "🤖 İndirim Takip Botu Aktif!\n\n"
        "Komutlar:\n"
        "/ekle <link> - Yeni ürün ekle\n"
        "/liste - Takip edilen ürünleri göster\n"
        "/sil <numara> - Ürün sil\n"
        "/yardim - Yardım mesajı"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Yardım mesajı"""
    await update.message.reply_text(
        "📋 Komut Listesi:\n\n"
        "/ekle <link> - Yeni ürün linki ekle\n"
        "  Örnek: /ekle https://www.gsstore.org/urun\n\n"
        "/liste - Takip edilen tüm ürünleri listele\n\n"
        "/sil <numara> - Belirtilen numaralı ürünü sil\n"
        "  Örnek: /sil 2\n\n"
        "/start - Botu başlat\n"
        "/yardim - Bu mesajı göster\n\n"
        "💡 Not: Bot her 30 dakikada bir otomatik kontrol yapar."
    )

async def add_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Yeni URL ekle"""
    if not context.args:
        await update.message.reply_text("❌ Kullanım: /ekle <link>")
        return
    
    url = " ".join(context.args).strip()
    
    if not url.startswith("http"):
        await update.message.reply_text("❌ Geçerli bir URL giriniz (http/https ile başlamalı)")
        return
    
    # Mevcut URL'leri oku
    existing_urls = []
    if os.path.exists(URLS_FILE):
        with open(URLS_FILE, "r", encoding="utf-8") as f:
            existing_urls = [line.strip() for line in f if line.strip()]
    
    if url in existing_urls:
        await update.message.reply_text("⚠️ Bu link zaten listede!")
        return
    
    # Ekle
    with open(URLS_FILE, "a", encoding="utf-8") as f:
        f.write(f"{url}\n")
    
    await update.message.reply_text(f"✅ Link eklendi!\n\n{url}\n\n📊 Toplam {len(existing_urls) + 1} ürün takip ediliyor.")

async def list_urls(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """URL'leri listele"""
    if not os.path.exists(URLS_FILE):
        await update.message.reply_text("📭 Henüz hiç ürün eklenmemiş.")
        return
    
    with open(URLS_FILE, "r", encoding="utf-8") as f:
        urls = [line.strip() for line in f if line.strip()]
    
    if not urls:
        await update.message.reply_text("📭 Henüz hiç ürün eklenmemiş.")
        return
    
    message = "📋 Takip Edilen Ürünler:\n\n"
    for i, url in enumerate(urls, 1):
        # URL'yi kısalt
        display_url = url if len(url) <= 60 else url[:57] + "..."
        message += f"{i}. {display_url}\n"
    
    message += f"\n📊 Toplam: {len(urls)} ürün"
    await update.message.reply_text(message)

async def remove_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """URL sil"""
    if not context.args:
        await update.message.reply_text("❌ Kullanım: /sil <numara>\n\nÖrnek: /sil 2")
        return
    
    try:
        index = int(context.args[0]) - 1
    except ValueError:
        await update.message.reply_text("❌ Geçerli bir numara giriniz")
        return
    
    if not os.path.exists(URLS_FILE):
        await update.message.reply_text("📭 Henüz hiç ürün eklenmemiş.")
        return
    
    with open(URLS_FILE, "r", encoding="utf-8") as f:
        urls = [line.strip() for line in f if line.strip()]
    
    if index < 0 or index >= len(urls):
        await update.message.reply_text(f"❌ Geçersiz numara! 1-{len(urls)} arasında bir sayı giriniz.")
        return
    
    removed_url = urls.pop(index)
    
    # Dosyayı yeniden yaz
    with open(URLS_FILE, "w", encoding="utf-8") as f:
        for url in urls:
            f.write(f"{url}\n")
    
    await update.message.reply_text(f"🗑️ Link silindi!\n\n{removed_url}\n\n📊 Kalan: {len(urls)} ürün")

async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bilinmeyen komut"""
    await update.message.reply_text(
        "❓ Bilinmeyen komut.\n\n"
        "Yardım için /yardim yazın."
    )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Hata yöneticisi"""
    logger.error(f"Hata oluştu: {context.error}")
    if update and update.message:
        await update.message.reply_text("⚠️ Bir hata oluştu. Lütfen tekrar deneyin.")

def main():
    """Bot'u başlat"""
    print("🤖 Telegram Bot başlatılıyor...")
    print(f"📱 Chat ID: {config.TELEGRAM_CHAT_ID}")
    
    # Application oluştur
    application = Application.builder().token(config.TELEGRAM_TOKEN).build()
    
    # Komut handler'ları ekle
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("yardim", help_command))
    application.add_handler(CommandHandler("ekle", add_url))
    application.add_handler(CommandHandler("liste", list_urls))
    application.add_handler(CommandHandler("sil", remove_url))
    
    # Bilinmeyen komutlar için
    application.add_handler(MessageHandler(filters.COMMAND, unknown_command))
    
    # Hata yöneticisi
    application.add_error_handler(error_handler)
    
    print("✅ Bot hazır! Mesajlar bekleniyor...")
    print("⚠️  Durdurmak için Ctrl+C basın")
    
    # Bot'u çalıştır
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
