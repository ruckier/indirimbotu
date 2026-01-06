import json
import os
import time
import random
import requests
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth
from fake_useragent import UserAgent

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
    """Mouse hareketleri ve scroll ile insan taklidi yapar."""
    try:
        # Rastgele mouse hareketleri
        for _ in range(random.randint(2, 5)):
            x = random.randint(100, 1000)
            y = random.randint(100, 800)
            page.mouse.move(x, y, steps=random.randint(5, 20))
            time.sleep(random.uniform(0.1, 0.5))
        
        # Rastgele scroll
        page.mouse.wheel(0, random.randint(100, 500))
        time.sleep(random.uniform(0.5, 2.0))
        page.mouse.wheel(0, -random.randint(50, 200)) # Geri çık
        time.sleep(random.uniform(0.5, 1.5))
    except Exception as e:
        print(f"Human behavior hatası: {e}")

def parse_price(text):
    if not text: return None
    # TL, simge vs temizle
    clean = text.replace("TL", "").replace("tl", "").replace("\n", "").strip()
    # 1.250,50 formatına uygun temizlik
    clean = clean.replace(".", "").replace(",", ".") 
    # Sadece sayı ve nokta kalsın
    clean = "".join([c for c in clean if c.isdigit() or c == '.'])
    try:
        return float(clean)
    except:
        return None

# --- SCRAPER (VERİ ÇEKİCİ) ---

def process_gsstore(page, url):
    products = []
    print(f"GSSTORE: {url}")
    if "giyim" in url or "aksesuar" in url or "koleksiyon" in url:
        try:
            page.wait_for_selector(".product-item", timeout=15000)
        except:
            print("GSStore ürünleri yüklenemedi.")
            return []
            
        items = page.locator(".product-item").all()
        for item in items:
            try:
                name_el = item.locator(".product-name").first
                name = name_el.inner_text().strip() if name_el.is_visible() else "GS Urunu"
                link_el = item.locator("a").first
                href = link_el.get_attribute("href")
                full_link = href if href.startswith("http") else "https://www.gsstore.org" + href
                price = None
                price_el = item.locator(".product-price .new-price, .product-price").first
                if price_el.is_visible():
                    price = parse_price(price_el.inner_text())
                if full_link and price:
                    products.append({"name": name, "url": full_link, "price": price})
            except: continue
    return products


# --- ANA MOTOR ---
def main():
    print("Bot Calisiyor... (Stealth Mode: ON)")
    
    if not os.path.exists(URLS_FILE):
        print("urls.txt bulunamadı!")
        return
        
    with open(URLS_FILE, "r") as f:
        urls = [line.strip() for line in f if line.strip()]

    old_prices = load_prices()
    new_prices = old_prices.copy()
    
    ua = UserAgent()
    user_agent = ua.random
    print(f"User-Agent: {user_agent[:30]}...")

    with sync_playwright() as p:
        # Stealth Tarayıcı Başlatma
        browser = p.chromium.launch(
            # Github Actions veya sunucuda ise headless=True olsun, değilse False
            headless=True if os.environ.get("GITHUB_ACTIONS") else False,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = browser.new_context(
            user_agent=user_agent,
            viewport={"width": 1366, "height": 768},
            locale="tr-TR",
            timezone_id="Europe/Istanbul"
        )
        
        page = context.new_page()
        # STEALTH PLUGİN AKTİF
        Stealth().apply_stealth_sync(page)

        for url in urls:
            try:
                print(f"\nSiteye Gidiliyor: {url}")
                page.goto(url, timeout=90000, wait_until="domcontentloaded")
                
                # İnsan gibi bekle ve hareket et
                time.sleep(random.uniform(2, 5))
                simulate_human_behavior(page)
                
                found_products = []
                if "gsstore" in url:
                    found_products = process_gsstore(page, url)
                else:
                    print("  -> Desteklenmeyen link, atlanıyor.")
                    continue
                
                print(f"   -> {len(found_products)} ürün çekildi.")
                
                # Fiyat Kontrolü
                for prod in found_products:
                    uid = prod["url"]
                    price = prod["price"]
                    name = prod["name"]
                    
                    if uid in old_prices:
                        old_price = old_prices[uid]["price"]
                        if price < old_price:
                            discount = int(((old_price - price) / old_price) * 100)
                            if discount >= 5:
                                msg = f"INDIRIM! (%{discount})\n\n{name}\nEski: {old_price} TL\nYeni: {price} TL\nLink: {uid}"
                                print(f"   Bildirim: {name}")
                                send_telegram(msg)
                    
                    new_prices[uid] = {
                        "name": name,
                        "price": price,
                        "updated_at": time.time()
                    }
                    
                time.sleep(random.uniform(3, 7)) # Rastgele bekleme
                
            except Exception as e:
                print(f"Genel Hata ({url}): {e}")

        browser.close()
        
    save_prices(new_prices)
    print("\nKontrol Tamamlandi.")

if __name__ == "__main__":
    main()
