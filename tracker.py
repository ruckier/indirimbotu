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
LAST_UPDATE_FILE = ".last_update_id"

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
    
    # Son işlenen update_id'yi oku
    last_update_id = 0
    if os.path.exists(LAST_UPDATE_FILE):
        try:
            with open(LAST_UPDATE_FILE, "r") as f:
                last_update_id = int(f.read().strip())
        except:
            pass
    
    # Mevcut URL'leri oku
    existing_urls = []
    if os.path.exists(URLS_FILE):
        with open(URLS_FILE, "r") as f:
            existing_urls = [line.strip() for line in f if line.strip()]

    max_update_id = last_update_id
    
    for update in updates:
        update_id = update.get("update_id", 0)
        
        # Sadece yeni mesajları işle
        if update_id <= last_update_id:
            continue
            
        if update_id > max_update_id:
            max_update_id = update_id
            
        if "message" in update and "text" in update["message"]:
            text = update["message"]["text"]
            chat_id = str(update["message"]["chat"]["id"])
            if chat_id != config.TELEGRAM_CHAT_ID: continue
            
            if text.startswith("/ekle "):
                url_to_add = text.split("/ekle ", 1)[1].strip()
                if url_to_add.startswith("http") and url_to_add not in existing_urls and url_to_add not in new_urls:
                    new_urls.append(url_to_add)
                    send_telegram(f"✅ Yeni link listeye eklendi: {url_to_add}")
    
    # Son işlenen update_id'yi kaydet
    if max_update_id > last_update_id:
        with open(LAST_UPDATE_FILE, "w") as f:
            f.write(str(max_update_id))
    
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
            time.sleep(0.5)
            
            # Mouse ile de aşağı in
            page.mouse.wheel(0, 10000)
            time.sleep(1)
            
            # "Daha Fazla Göster" butonu varsa tıkla
            try:
                load_more = page.locator(".action.more, .btn-load-more, button.load-more").first
                if load_more.is_visible():
                    print("   'Daha Fazla Göster' butonu bulundu, tıklanıyor...")
                    load_more.click()
                    time.sleep(2)
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

    # SCROLL ÇAĞRISI (Ürünleri yükle) - Liste sayfasıysa işe yarar
    print("   [DEBUG] process_gsstore içinde scroll başlatılıyor...")
    simulate_human_behavior(page)
    time.sleep(2)

    # 1. YÖNTEM: LİSTE SAYFASI TARAMA
    items = page.locator(".product-item").all()
    if not items:
        items = page.locator(".product-item-info").all()

    if items:
        print(f"   {len(items)} adet liste öğesi (kart) inceleniyor...")
        for item in items:
            try:
                full_text = item.inner_text().replace("\n", " ")
                price = find_price_in_text(full_text)
                
                name = "İsimsiz Ürün"
                link_el = item.locator("a").first
                href = link_el.get_attribute("href")
                
                if link_el.count() > 0:
                    name_candidate = link_el.get_attribute("title")
                    if not name_candidate:
                        name_candidate = link_el.inner_text().strip()
                    if name_candidate and len(name_candidate) > 3: 
                        name = name_candidate

                if len(name) < 5 or "İsimsiz" in name:
                    possible_names = item.locator("[class*='name'], [class*='title']").all_inner_texts()
                    for p in possible_names:
                         if len(p.strip()) > 5:
                             name = p.strip()
                             break
                
                full_link = None
                if href:
                    full_link = href if href.startswith("http") else "https://www.gsstore.org" + href

                image_url = ""
                try:
                    img_el = item.locator("img").first
                    if img_el.count() > 0:
                        image_url = img_el.get_attribute("src")
                        if not image_url or "placeholder" in image_url:
                            data_src = img_el.get_attribute("data-src")
                            if data_src: image_url = data_src
                except: pass

                if full_link and price:
                    if str(price) in name:
                        name = name.replace(str(price), "").replace("TL", "").strip()
                    products.append({
                        "name": name, 
                        "url": full_link, 
                        "price": price,
                        "image": image_url
                    })
            except Exception as e: 
                continue
        return products

    # 2. YÖNTEM: TEKİL ÜRÜN SAYFASI (Detail Page)
    # Eğer liste öğesi bulunamadıysa, buranın bir ürün sayfası olup olmadığına bak.
    print("   -> Liste öğesi bulunamadı, tekil ürün sayfası mı diye bakılıyor...")
    try:
        # Fiyat kontrolü
        price_box = page.locator(".price-box.price-final_price").first
        if price_box.is_visible():
            raw_price = price_box.inner_text()
            price = find_price_in_text(raw_price)
            
            if price:
                # İsim
                name_el = page.locator("h1.page-title").first
                name = name_el.inner_text().strip() if name_el.is_visible() else "Detay Sayfası Ürünü"
                
                # Resim
                image = ""
                img_el = page.locator(".gallery-placeholder__image").first
                if not img_el.is_visible():
                     img_el = page.locator(".fotorama__img").first
                
                if img_el.is_visible():
                    image = img_el.get_attribute("src")
                
                print(f"   -> TEKİL ÜRÜN BULUNDU: {name} - {price} TL")
                products.append({
                    "name": name,
                    "url": url, # Tekil sayfa olduğu için URL kendisidir
                    "price": price,
                    "image": image if image else ""
                })
                return products
    except Exception as e:
        print(f"   -> Tekil ürün tarama hatası: {e}")

    print("!!! HİÇ ÜRÜN BULUNAMADI (Liste veya Tekil) !!!")
    return []

def process_saatvesaat(page, url):
    products = []
    print(f"SAAT&SAAT: {url}")
    try:
        page.wait_for_load_state("domcontentloaded", timeout=20000)

        # --- LİSTE SAYFASI KONTROLÜ ---
        # Önce scroll yapalım ki lazy load ürünler gelsin
        simulate_human_behavior(page)
        
        items = page.locator(".product-item").all()
        if not items:
            items = page.locator(".product-item-info").all()

        if items:
            print(f"   {len(items)} adet liste öğesi (kart) inceleniyor...")
            for item in items:
                try:
                    # İsim ve Link
                    name = "İsimsiz Saat"
                    link_el = item.locator("a.product-item-link").first
                    if not link_el.is_visible():
                         link_el = item.locator("a").first
                    
                    full_link = url
                    if link_el.count() > 0:
                        name = link_el.inner_text().strip()
                        href = link_el.get_attribute("href")
                        if href:
                            full_link = href if href.startswith("http") else "https://www.saatvesaat.com.tr" + href

                    # Fiyat
                    price = None
                    price_el = item.locator(".special-price .price").first
                    if not price_el.is_visible():
                        price_el = item.locator(".price-box .price").first
                    
                    if price_el.is_visible():
                         raw_price = price_el.inner_text()
                         price = find_price_in_text(raw_price)

                    # Resim
                    image = ""
                    try:
                        img_el = item.locator("img.product-image-photo").first
                        if img_el.is_visible():
                            image = img_el.get_attribute("src")
                    except: pass

                    if price:
                        products.append({
                            "name": name, 
                            "url": full_link, 
                            "price": price,
                            "image": image if image else ""
                        })
                except Exception as e:
                    continue
            
            if products:
                return products

        # --- TEKİL ÜRÜN SAYFASI (ESKİ MANTIK) ---
        print("   -> Liste bulunamadı, tekil ürün kontrolü yapılıyor...")
        
        # Fiyat kontrolü
        price = None
        
        # 1. Deneme: .product-info-main .price
        try:
            price_el = page.locator(".product-info-main .price").first
            if price_el.is_visible():
                 raw_price = price_el.inner_text()
                 price = find_price_in_text(raw_price)
        except: pass
        
        # 2. Deneme: .special-price .price (Indirimli)
        if not price:
             try:
                price_el = page.locator(".special-price .price").first
                if price_el.is_visible():
                    raw_price = price_el.inner_text()
                    price = find_price_in_text(raw_price)
             except: pass

        # 3. Deneme: Meta tag
        if not price:
            try:
                meta_price = page.locator('meta[property="product:price:amount"]').first.get_attribute("content")
                if meta_price:
                    price = float(meta_price)
            except: pass
        
        if price:
            # İsim
            name = "Saat&Saat Ürünü"
            try:
                name_el = page.locator("h1.page-title").first
                if not name_el.is_visible():
                     name_el = page.locator("h1").first
                if name_el.is_visible():
                    name = name_el.inner_text().strip()
            except: pass
            
            # Resim
            image = ""
            try:
                img_el = page.locator(".gallery-placeholder__image").first
                if not img_el.is_visible():
                        img_el = page.locator(".fotorama__img").first
                
                if img_el.is_visible():
                    image = img_el.get_attribute("src")
            except: pass
            
            print(f"   -> SAAT&SAAT BULDU: {name} - {price} TL")
            products.append({
                "name": name,
                "url": url,
                "price": price,
                "image": image if image else ""
            })
        else:
            print("   -> Fiyat elementini bulamadım, generic scraper deneyelim...")

    except Exception as e:
        print(f"   Saat ve Saat Scraper Hatası: {e}")
            
    return products

# --- ANA MOTOR ---
def main():
    print("--- V3.0 FINAL FIX ---")
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
                time.sleep(random.uniform(1, 2.5))
                # simulate_human_behavior(page) -> KALDIRILDI, process_gsstore icine tasindi
                
                found_products = []
                if "gsstore" in url:
                    found_products = process_gsstore(page, url)
                elif "saatvesaat" in url:
                    found_products = process_saatvesaat(page, url)
                else:
                    # Generic scraper denemesi
                    print("  -> GSStore değil, geneleksel tarayıcı (generic scraper) devreye giriyor.")
                    from playwright.sync_api import TimeoutError
                    
                    try:
                        # 1. Title/Name
                        name = "Bilinmeyen Ürün"
                        try:
                            og_title = page.locator('meta[property="og:title"]').first.get_attribute("content")
                            if og_title: name = og_title
                            else: name = page.title()
                        except: name = page.title()

                        # 2. Image
                        image = ""
                        try:
                            og_image = page.locator('meta[property="og:image"]').first.get_attribute("content")
                            if og_image: image = og_image
                            else:
                                # Fallback: En büyük resmi bulmaya calis (basit bir mantik)
                                imgs = page.locator("img").all()
                                for img in imgs[:5]: # Ilk 5 resme bak
                                    if img.is_visible() and int(img.get_attribute("width") or 0) > 200:
                                        image = img.get_attribute("src")
                                        break
                        except: pass

                        # 3. Price
                        price = None
                        try:
                            # Tüm text icinde ara
                            body_text = page.inner_text("body")
                            # Regex ile fiyat ara (find_price_in_text fonksiyonunu kullan)
                            price = find_price_in_text(body_text[:5000]) # Ilk 5000 karakter yeterli olabilir
                            
                            # Eger genel textte bulamazsa, belli classlara bak
                            if not price:
                                price_candidates = page.locator("[class*='price'], [id*='price']").all_inner_texts()
                                for pc in price_candidates:
                                    found = find_price_in_text(pc)
                                    if found:
                                        price = found
                                        break
                        except: pass

                        if price and price > 0:
                             print(f"   GENERIC BULDU: {name} - {price} TL")
                             found_products = [{
                                 "name": name.strip(),
                                 "url": url,
                                 "price": price,
                                 "image": image
                             }]
                        else:
                             print("   -> Generic scraper fiyat bulamadı.")
                             
                    except Exception as ge:
                         print(f"   Generic scraper hatası: {ge}")

                
                print(f"   -> {len(found_products)} ürün çekildi.")
                
                for prod in found_products:
                    uid = prod["url"]
                    price = prod["price"]
                    name = prod["name"]
                    image = prod.get("image", "")
                    
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
                        "image": image,
                        "updated_at": last_updated
                    }
                time.sleep(random.uniform(1.5, 3))
            except Exception as e:
                print(f"Genel Hata ({url}): {e}")

        browser.close()
        
    save_prices(new_prices)
    print("\nKontrol Tamamlandi.")
    
    if not discount_found:
        send_telegram("Kontrol ettim, herhangi bir değişiklik yok.")

if __name__ == "__main__":
    main()
