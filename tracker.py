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
def process_amazon(page, url):
    products = []
    if "/s?" in url or "wishlist" in url or "/hz/" in url:
        print(f"AMAZON Liste: {url}")
        page.wait_for_timeout(3000)
        items = page.locator("div[data-component-type='s-search-result'], li.g-item-sortable").all()
        for item in items:
            try:
                link_el = item.locator("a.a-link-normal").first
                if not link_el.is_visible(): continue
                href = link_el.get_attribute("href")
                if not href: continue
                full_link = "https://www.amazon.com.tr" + href.split("/ref=")[0]
                name_el = item.locator("h2, a[title], .a-text-normal").first
                name = name_el.inner_text().strip() if name_el.is_visible() else "Amazon Urunu"
                price = None
                price_el = item.locator(".a-price-whole").first
                if price_el.is_visible():
                    price = parse_price(price_el.inner_text())
                if full_link and price:
                    products.append({"name": name, "url": full_link, "price": price})
            except: continue
    else:
        print(f"AMAZON Ürün: {url}")
        try:
            name_el = page.locator("#productTitle")
            name = name_el.inner_text().strip() if name_el.is_visible() else "Amazon Urunu"
            price_el = page.locator(".a-price-whole, #price_inside_buybox").first
            price = parse_price(price_el.inner_text()) if price_el.is_visible() else None
            if price:
                products.append({"name": name, "url": url, "price": price})
        except Exception as e:
            print(f"Amazon Hata: {e}")
    return products

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

def process_pull_and_bear(page, url):
    """Pull & Bear için JSON-LD ve HTML analizi yapar."""
    print(f"PULL&BEAR Taranıyor: {url}")
    products = []
    try:
        simulate_human_behavior(page)
        
        # Yöntem 1: JSON-LD (En Temiz Yöntem)
        # Sayfanın arka planındaki yapısal veriyi okur.
        try:
            json_data = page.evaluate("""() => {
                const script = document.querySelector('script[type="application/ld+json"]');
                return script ? JSON.parse(script.innerText) : null;
            }""")
            
            if json_data:
                # Veri bazen liste [{}, {}] bazen tek obje {} gelir
                data = json_data[0] if isinstance(json_data, list) else json_data
                
                # Ürün ismi ve Fiyatı
                name = data.get("name")
                price = None
                
                offers = data.get("offers")
                if offers:
                    offers = offers[0] if isinstance(offers, list) else offers
                    price = float(offers.get("price", 0))
                
                if name and price:
                    print("   -> JSON-LD üzerinden veri alındı.")
                    products.append({"name": name, "url": url, "price": price})
                    return products
        except Exception as e:
            print(f"   JSON-LD okunamadı, HTML deneniyor: {e}")

        # Yöntem 2: HTML Parsing (Yedek)
        # JS yüklenmesini bekle
        try:
            page.wait_for_selector("h1", timeout=15000)
        except:
            print("   -> Sayfa tam yüklenemedi.")
        
        # İsim (Genelde H1)
        name_el = page.locator("h1").first
        name = name_el.inner_text().strip() if name_el.is_visible() else "Pull&Bear Urun"
        
        # Fiyat (Karmaşık - TL içeren elementleri tara)
        price = None
        # Fiyat genelde bu class'larda olur ama değişebilir, geniş arayalım
        potential_prices = page.locator("span, div").filter(has_text="TL").all()
        
        prices_found = []
        for p_el in potential_prices:
            # Sadece görünür olanlar
            if not p_el.is_visible(): continue
            
            text = p_el.inner_text().strip()
            # Çok uzun metin değilse ve sayı içeriyorsa
            if len(text) < 30 and any(c.isdigit() for c in text):
                p = parse_price(text)
                if p: prices_found.append(p)
        
        if prices_found:
            # Genelde sayfadaki en düşük fiyat indirimli fiyattır (veya mevcut fiyattır)
            # Ancak bazen taksit seçenekleri vs. karışabilir.
            # Genellikle ilk bulunan veya min/max mantığı.
            # Şimdilik en düşüğü alalım (indirimli fiyat mantığı)
            price = min(prices_found)
            
        if price:
            products.append({"name": name, "url": url, "price": price})
        
    except Exception as e:
        print(f"Pull&Bear Hata: {e}")
    
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
                if "amazon" in url:
                    found_products = process_amazon(page, url)
                elif "gsstore" in url:
                    found_products = process_gsstore(page, url)
                elif "pullandbear" in url or "zara" in url or "bershka" in url:
                    found_products = process_pull_and_bear(page, url)
                else:
                    print("  -> Tanımsız site, sadece erişim denendi.")
                
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
