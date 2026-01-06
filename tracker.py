import json
import os
import time
import random
import requests
import re
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth
# from fake_useragent import UserAgent (Gerek kalmadı, elle veriyoruz)

# --- AYARLAR ---
URLS_FILE = "urls.txt"
PRICES_FILE = "prices.json"
CONFIG_FILE = "config.py"

# Telegram Fonksiyonları
try:
    import config
except ImportError:
    class Config:
        TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
        TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
    config = Config()

def send_telegram(message):
    if not config.TELEGRAM_TOKEN or not config.TELEGRAM_CHAT_ID:
        print("Telegram ayarları eksik, mesaj atılamadı.")
        return

    url = f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": config.TELEGRAM_CHAT_ID, "text": message}
    try:
        requests.post(url, data=payload, timeout=10)
    except Exception as e:
        print(f"Telegram hatası: {e}")

def get_telegram_updates():
    if not config.TELEGRAM_TOKEN: return []
    url = f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/getUpdates"
    try:
        response = requests.get(url, timeout=10).json()
        if response.get("ok"):
            return response["result"]
    except Exception as e:
        print(f"Telegram update hatası: {e}")
    return []

def check_new_urls():
    """Telegramdan gelen /ekle komutlarini kontrol eder."""
    updates = get_telegram_updates()
    new_urls = []
    
    # Mevcut URL'leri oku
    existing_urls = []
    if os.path.exists(URLS_FILE):
        with open(URLS_FILE, "r") as f:
            existing_urls = [line.strip() for line in f if line.strip()]

    for update in updates:
        if "message" in update and "text" in update["message"]:
            text = update["message"]["text"]
            chat_id = str(update["message"]["chat"]["id"])
            if chat_id != config.TELEGRAM_CHAT_ID: continue
            
            if text.startswith("/ekle "):
                url_to_add = text.split("/ekle ", 1)[1].strip()
                if url_to_add.startswith("http") and url_to_add not in existing_urls and url_to_add not in new_urls:
                    new_urls.append(url_to_add)
                    send_telegram(f"✅ Yeni link listeye eklendi: {url_to_add}")
    
    if new_urls:
        with open(URLS_FILE, "a") as f:
            for url in new_urls:
                f.write(f"\n{url}")
        print(f"{len(new_urls)} yeni link eklendi.")

def send_telegram_photo(message, photo_path):
    if not config.TELEGRAM_TOKEN or not config.TELEGRAM_CHAT_ID:
        return

    url = f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendPhoto"
    payload = {"chat_id": config.TELEGRAM_CHAT_ID, "caption": message}
    try:
        with open(photo_path, 'rb') as f:
            files = {'photo': f}
            requests.post(url, data=payload, files=files, timeout=20)
    except Exception as e:
        print(f"Telegram Foto hatası: {e}")

# --- KAYIT SİSTEMİ ---
def load_prices():
    if os.path.exists(PRICES_FILE):
        try:
            with open(PRICES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_prices(data):
    with open(PRICES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# --- İNSAN TAKLİDİ VE YARDIMCILAR ---
def simulate_human_behavior(page):
    """Sayfanın sonuna kadar scroll yaparak lazy load tetikler."""
    print(">>> SCROLL BAŞLIYOR <<<")
    try:
        # Önceki yükseklik
        last_height = page.evaluate("document.body.scrollHeight")
        
        for i in range(10): # Maksimum 10 sayfa/tur scroll
            print(f"   Scroll Turu: {i+1}")
            
            # Klavye ile 'End' tuşuna bas (Daha etkili)
            page.keyboard.press("End")
            time.sleep(1)
            
            # Mouse ile de aşağı in
            page.mouse.wheel(0, 10000)
            time.sleep(2)
            
            # "Daha Fazla Göster" butonu varsa tıkla
            try:
                load_more = page.locator(".action.more, .btn-load-more, button.load-more").first
                if load_more.is_visible():
                    print("   'Daha Fazla Göster' butonu bulundu, tıklanıyor...")
                    load_more.click()
                    time.sleep(3)
            except: pass

            # Yeni yükseklik kontrolü
            new_height = page.evaluate("document.body.scrollHeight")
            if new_height == last_height:
                print("   Sayfa sonuna gelindi (Yükseklik değişmedi).")
                break 
            last_height = new_height
            
        print(">>> SCROLL BİTTİ <<<")
        
    except Exception as e:
        print(f"Human behavior hatası: {e}")

def parse_price(text):
    if not text: return None
    clean = text.replace("TL", "").replace("tl", "").replace("\n", "").strip()
    clean = clean.replace(".", "").replace(",", ".") 
    clean = "".join([c for c in clean if c.isdigit() or c == '.'])
    try:
        return float(clean)
    except:
        return None

def find_price_in_text(text):
    # Metin içindeki 1.250,00 TL veya 1250 TL gibi ifadeleri bulur
    matches = re.findall(r'([\d\.,]+)\s*(?:TL|tl)', text)
    if not matches:
        matches = re.findall(r'(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)', text)
    
    if matches:
        for m in matches:
            val = parse_price(m)
            if val and 10 < val < 100000: # Mantıklı fiyat aralığı
                return val
    return None

# --- SCRAPER (VERİ ÇEKİCİ) ---
def process_gsstore(page, url):
    products = []
    print(f"GSSTORE: {url}")
    
    try:
        print(f"   Sayfa Başlığı: {page.title()}")
    except: pass

    # SCROLL ÇAĞRISI (Ürünleri yükle)
    print("   [DEBUG] process_gsstore içinde scroll başlatılıyor...")
    simulate_human_behavior(page)
    time.sleep(2)

    # Ürünleri topla
    items = page.locator(".product-item").all()
    if not items:
        # Tekrar dene (belki scroll sonrası DOM değişti)
        items = page.locator(".product-item").all()
    if not items:
        items = page.locator(".product-item-info").all()

    if not items:
        print("!!! HİÇ ÜRÜN BULUNAMADI !!!")
        try:
            print(page.inner_html("body")[:500])
        except: pass
        return []

    print(f"   {len(items)} adet kart inceleniyor...")
    
    for item in items:
        try:
            # Tüm kartın metnini al
            full_text = item.inner_text().replace("\n", " ")
            price = find_price_in_text(full_text)
            
            name = "İsimsiz Ürün"
            
            # 1. Yöntem: Link
            link_el = item.locator("a").first
            href = link_el.get_attribute("href")
            
            if link_el.count() > 0:
                name_candidate = link_el.get_attribute("title")
                if not name_candidate:
                    name_candidate = link_el.inner_text().strip()
                if name_candidate and len(name_candidate) > 3: 
                    name = name_candidate

            # 2. Yöntem: Class tarama
            if len(name) < 5 or "İsimsiz" in name:
                possible_names = item.locator("[class*='name'], [class*='title']").all_inner_texts()
                for p in possible_names:
                     if len(p.strip()) > 5:
                         name = p.strip()
                         break
            
            full_link = None
            if href:
                full_link = href if href.startswith("http") else "https://www.gsstore.org" + href

            if full_link and price:
                if str(price) in name:
                    name = name.replace(str(price), "").replace("TL", "").strip()
                products.append({"name": name, "url": full_link, "price": price})
                
        except Exception as e: 
            continue
            
    return products

# --- ANA MOTOR ---
def main():
    print("--- V2.1 INFINITE SCROLL ---")
    print("Bot Calisiyor... (Stealth Mode: ON)")
    check_new_urls()
    discount_found = False
    
    if not os.path.exists(URLS_FILE):
        print("urls.txt bulunamadı!")
        return
        
    with open(URLS_FILE, "r") as f:
        urls = [line.strip() for line in f if line.strip()]

    old_prices = load_prices()
    new_prices = old_prices.copy()
    
    # User-Agent: Masaüstü Sabit
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    print(f"User-Agent: {user_agent}")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True if os.environ.get("GITHUB_ACTIONS") else False,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = browser.new_context(
            user_agent=user_agent,
            viewport={"width": 1920, "height": 1080},
            locale="tr-TR",
            timezone_id="Europe/Istanbul"
        )
        
        page = context.new_page()
        Stealth().apply_stealth_sync(page)

        for url in urls:
            try:
                print(f"\nSiteye Gidiliyor: {url}")
                page.goto(url, timeout=90000, wait_until="domcontentloaded")
                time.sleep(random.uniform(2, 5))
                # simulate_human_behavior(page) -> KALDIRILDI, process_gsstore icine tasindi
                
                found_products = []
                if "gsstore" in url:
                    found_products = process_gsstore(page, url)
                else:
                    print("  -> Desteklenmeyen link, atlanıyor.")
                    continue
                
                print(f"   -> {len(found_products)} ürün çekildi.")
                
                for prod in found_products:
                    uid = prod["url"]
                    price = prod["price"]
                    name = prod["name"]
                    
                    last_updated = time.time()
                    price_changed = True

                    if uid in old_prices:
                        old_price = old_prices[uid]["price"]
                        if price == old_price:
                            price_changed = False
                            last_updated = old_prices[uid]["updated_at"]
                        elif price < old_price:
                            discount = int(((old_price - price) / old_price) * 100)
                            if discount >= 5:
                                msg = f"INDIRIM! (%{discount})\n\n{name}\nEski: {old_price} TL\nYeni: {price} TL\nLink: {uid}"
                                print(f"   Bildirim: {name}")
                                
                                screenshot_path = f"screenshot_{int(time.time())}.png"
                                try:
                                    page.screenshot(path=screenshot_path)
                                    send_telegram_photo(msg, screenshot_path)
                                    os.remove(screenshot_path)
                                except Exception as err:
                                    print(f"Screenshot hatası: {err}")
                                    send_telegram(msg)
                                discount_found = True
                    
                    new_prices[uid] = {
                        "name": name,
                        "price": price,
                        "updated_at": last_updated
                    }
                time.sleep(random.uniform(3, 7))
            except Exception as e:
                print(f"Genel Hata ({url}): {e}")

        browser.close()
        
    save_prices(new_prices)
    print("\nKontrol Tamamlandi.")
    
    if not discount_found:
        send_telegram("Kontrol ettim, herhangi bir değişiklik yok.")

if __name__ == "__main__":
    main()
