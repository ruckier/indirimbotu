"""
Gelişmiş Saat&Saat Scraper
Anti-detection ve çoklu strateji ile Saat&Saat sitesinden ürün bilgisi çeker
"""

import time
import random
import json
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from playwright_stealth import Stealth

# Test URL'leri
TEST_LIST_URL = "https://www.saatvesaat.com.tr/erkek-klasik-saat?filters[brand.f]=seiko+5&order=position&direction=desc&pi=2"
TEST_PRODUCT_URL = "https://www.saatvesaat.com.tr/seiko-5-erkek-kol-saati-p-s5-srpj85k"

def get_random_user_agent():
    """Rastgele gerçekçi user agent döndürür"""
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15"
    ]
    return random.choice(user_agents)

def parse_price(text):
    """Fiyat metnini sayıya çevirir"""
    if not text:
        return None
    
    # TL, TL harflerini temizle
    clean = text.replace("TL", "").replace("tl", "").replace("₺", "").replace("\n", "").strip()
    
    # Türk formatı: 1.299,99 -> 1299.99
    clean = clean.replace(".", "").replace(",", ".")
    
    # Sadece sayı ve nokta kalsın
    clean = "".join([c for c in clean if c.isdigit() or c == '.'])
    
    try:
        return float(clean)
    except:
        return None

def advanced_scrape_saatvesaat(url, headless=True):
    """
    Gelişmiş Saat&Saat scraper
    - Stealth mode
    - Gerçekçi header'lar
    - Cookie kabul etme
    - Ekstra beklemeler
    - Çoklu selector stratejisi
    """
    products = []
    
    user_agent = get_random_user_agent()
    print(f"\nSaat&Saat Scraping Baslat iliyor...")
    print(f"   URL: {url}")
    print(f"   User-Agent: {user_agent[:50]}...")
    
    with sync_playwright() as p:
        # Browser başlat - Gerçekçi parametrelerle
        browser = p.chromium.launch(
            headless=headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process"
            ]
        )
        
        # Context oluştur - Gerçekçi browser davranışı
        context = browser.new_context(
            user_agent=user_agent,
            viewport={"width": 1920, "height": 1080},
            locale="tr-TR",
            timezone_id="Europe/Istanbul",
            color_scheme="light",
            device_scale_factor=1,
            has_touch=False,
            is_mobile=False,
            # Extra headers
            extra_http_headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
                "Accept-Encoding": "gzip, deflate, br",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Cache-Control": "max-age=0"
            }
        )
        
        # Page oluştur ve stealth uygula
        page = context.new_page()
        stealth_config = Stealth()
        stealth_config.apply_stealth_sync(page)
        
        # WebDriver detection'ı daha da azalt
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            window.chrome = {
                runtime: {}
            };
            
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            
            Object.defineProperty(navigator, 'languages', {
                get: () => ['tr-TR', 'tr', 'en-US', 'en']
            });
        """)
        
        try:
            # Sayfayı aç
            print("   Sayfa yukleniyor...")
            page.goto(url, timeout=60000, wait_until="domcontentloaded")
            
            # İnsan gibi bekle
            time.sleep(random.uniform(2, 4))
            
            # Cookie kabul et (varsa)
            try:
                cookie_selectors = [
                    "button:has-text('Kabul')",
                    "button:has-text('Tamam')",
                    "button:has-text('Anladım')",
                    ".cookie-accept",
                    "#cookieAccept",
                    "[id*='cookie'][id*='accept']"
                ]
                for selector in cookie_selectors:
                    try:
                        btn = page.locator(selector).first
                        if btn.is_visible(timeout=2000):
                            print("   Cookie kabul ediliyor...")
                            btn.click()
                            time.sleep(1)
                            break
                    except:
                        continue
            except:
                pass
            
            # Sayfayı scroll et - Lazy loading için
            print("   Sayfa scroll ediliyor...")
            for i in range(5):
                page.keyboard.press("End")
                time.sleep(0.5)
                page.mouse.wheel(0, 5000)
                time.sleep(1)
            
            # Başa dön
            page.keyboard.press("Home")
            time.sleep(1)
            
            # Network idle bekle
            try:
                page.wait_for_load_state("networkidle", timeout=10000)
            except:
                pass
            
            print("   Urunler aranıyor...")
            
            # STRATEJİ 1: Liste sayfası - Çoklu selector
            product_selectors = [
                ".product-item",
                ".product-item-info",
                ".product-card",
                "[class*='product-item']",
                "[class*='ProductItem']",
                ".item.product"
            ]
            
            items = []
            for selector in product_selectors:
                try:
                    items = page.locator(selector).all()
                    if items:
                        print(f"   >> {len(items)} urun bulundu (selector: {selector})")
                        break
                except:
                    continue
            
            if items:
                print(f"   >> {len(items)} urun isleniyor...")
                for idx, item in enumerate(items[:50]):  # Max 50 ürün
                    try:
                        # İsim ve Link - Çoklu strateji
                        name = "Saat&Saat Ürünü"
                        product_url = url
                        
                        link_selectors = [
                            "a.product-item-link",
                            "a[class*='product-name']",
                            "a[class*='ProductName']",
                            "a.product-link",
                            ".product-name a",
                            "a[href*='/p-']"
                        ]
                        
                        for link_sel in link_selectors:
                            try:
                                link_el = item.locator(link_sel).first
                                if link_el.count() > 0:
                                    name_text = link_el.inner_text(timeout=2000).strip()
                                    if name_text and len(name_text) > 3:
                                        name = name_text
                                    
                                    href = link_el.get_attribute("href")
                                    if href:
                                        product_url = href if href.startswith("http") else f"https://www.saatvesaat.com.tr{href}"
                                    break
                            except:
                                continue
                        
                        # Fiyat - Çoklu strateji
                        price = None
                        price_selectors = [
                            ".special-price .price",
                            ".price-box .price",
                            "[class*='special-price']",
                            "[class*='Price']",
                            ".price",
                            "[data-price-amount]"
                        ]
                        
                        for price_sel in price_selectors:
                            try:
                                price_el = item.locator(price_sel).first
                                if price_el.is_visible(timeout=2000):
                                    price_text = price_el.inner_text()
                                    price = parse_price(price_text)
                                    if price:
                                        break
                            except:
                                continue
                        
                        # Son çare: Tüm metinden fiyat ara
                        if not price:
                            try:
                                full_text = item.inner_text()
                                import re
                                matches = re.findall(r'([\d\.,]+)\s*(?:TL|₺)', full_text)
                                if matches:
                                    for match in matches:
                                        price = parse_price(match)
                                        if price and 10 < price < 1000000:
                                            break
                            except:
                                pass
                        
                        # Resim
                        image = ""
                        try:
                            img_el = item.locator("img").first
                            if img_el.count() > 0:
                                image = img_el.get_attribute("src") or img_el.get_attribute("data-src") or ""
                        except:
                            pass
                        
                        if price and price > 0:
                            products.append({
                                "name": name,
                                "url": product_url,
                                "price": price,
                                "image": image
                            })
                            print(f"      [OK] {idx+1}. {name[:40]}... - {price} TL")
                        
                    except Exception as e:
                        continue
                
                if products:
                    print(f"\n   [BASARILI] Toplam {len(products)} urun basariyla cekildi!")
                    return products
            
            # STRATEJİ 2: Tekil ürün sayfası
            print("   Tekil urun kontrolu yapiliyor...")
            
            # Fiyat bul - Çoklu selector
            price = None
            price_selectors = [
                ".product-info-main .price",
                ".special-price .price",
                ".price-box .price",
                "[class*='product-price']",
                "[data-price-type='finalPrice']",
                "meta[property='product:price:amount']"
            ]
            
            for sel in price_selectors:
                try:
                    if sel.startswith("meta"):
                        price_val = page.locator(sel).first.get_attribute("content")
                        if price_val:
                            price = float(price_val)
                            break
                    else:
                        price_el = page.locator(sel).first
                        if price_el.is_visible(timeout=3000):
                            price_text = price_el.inner_text()
                            price = parse_price(price_text)
                            if price:
                                print(f"   [FIYAT] {price} TL (selector: {sel})")
                                break
                except:
                    continue
            
            if price:
                # İsim
                name = "Saat&Saat Ürünü"
                name_selectors = [
                    "h1.page-title",
                    "h1[class*='product-name']",
                    "h1",
                    ".product-name",
                    "meta[property='og:title']"
                ]
                
                for sel in name_selectors:
                    try:
                        if sel.startswith("meta"):
                            name = page.locator(sel).first.get_attribute("content")
                            if name:
                                break
                        else:
                            name_el = page.locator(sel).first
                            if name_el.is_visible(timeout=2000):
                                name = name_el.inner_text().strip()
                                break
                    except:
                        continue
                
                # Resim
                image = ""
                img_selectors = [
                    ".gallery-placeholder__image",
                    ".fotorama__img",
                    ".product-image-photo",
                    "meta[property='og:image']"
                ]
                
                for sel in img_selectors:
                    try:
                        if sel.startswith("meta"):
                            image = page.locator(sel).first.get_attribute("content")
                            if image:
                                break
                        else:
                            img_el = page.locator(sel).first
                            if img_el.is_visible(timeout=2000):
                                image = img_el.get_attribute("src") or ""
                                break
                    except:
                        continue
                
                products.append({
                    "name": name,
                    "url": url,
                    "price": price,
                    "image": image
                })
                
                print(f"   [OK] Tekil urun bulundu: {name} - {price} TL")
                return products
            
            print("   [UYARI] Hic urun bulunamadi!")
            
        except Exception as e:
            print(f"   [HATA] {e}")
        finally:
            browser.close()
    
    return products

def test_scraper():
    """Test fonksiyonu"""
    print("="*60)
    print("SAAT&SAAT GELISMIS SCRAPER TESTI")
    print("="*60)
    
    # Test 1: Liste sayfasi
    print("\nTEST 1: Liste Sayfasi")
    print("-"*60)
    products = advanced_scrape_saatvesaat(TEST_LIST_URL, headless=False)
    
    if products:
        print(f"\nSonuc: {len(products)} urun bulundu")
        print("\nIlk 3 urun:")
        for idx, p in enumerate(products[:3], 1):
            print(f"\n{idx}. {p['name']}")
            print(f"   Fiyat: {p['price']} TL")
            print(f"   Link: {p['url'][:80]}...")
    else:
        print("\nHic urun bulunamadi!")
    
    # Test 2: Tekil urun
    print("\n" + "="*60)
    print("\nTEST 2: Tekil Urun Sayfasi")
    print("-"*60)
    products2 = advanced_scrape_saatvesaat(TEST_PRODUCT_URL, headless=False)
    
    if products2:
        print(f"\nSonuc: Urun bulundu")
        p = products2[0]
        print(f"\nUrun: {p['name']}")
        print(f"Fiyat: {p['price']} TL")
        print(f"Resim: {p['image'][:80]}...")
    else:
        print("\nUrun bulunamadi!")
    
    print("\n" + "="*60)
    print("Test tamamlandi!")
    print("="*60)

if __name__ == "__main__":
    test_scraper()
