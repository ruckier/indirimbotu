from playwright.sync_api import sync_playwright
import time
import re

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
    matches = re.findall(r'([\d\.,]+)\s*(?:TL|tl)', text)
    if not matches:
        matches = re.findall(r'(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)', text)
    
    if matches:
        for m in matches:
            val = parse_price(m)
            if val and 10 < val < 100000:
                return val
    return None

def process_saatvesaat(page, url):
    products = []
    print(f"Testing SAAT&SAAT: {url}")
    try:
        page.wait_for_load_state("domcontentloaded", timeout=20000)

        # Skip simulate_human_behavior for quick test, or keep basic scroll
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(2)
        
        # Check text content for debugging
        # print(page.content())

        # --- TEKİL ÜRÜN SAYFASI TEST ---
        print("   -> Tekil ürün kontrolü yapılıyor...")
        
        price = None
        
        # Selector checks
        selectors = [
            ".product-info-main .price",
            ".special-price .price",
            ".price-box .price",
            "[data-price-amount]"
        ]
        
        for sel in selectors:
            try:
                el = page.locator(sel).first
                if el.is_visible():
                    print(f"Found visible selector: {sel}")
                    raw = el.inner_text()
                    print(f"Content: {raw}")
                    price = find_price_in_text(raw)
                    if price: break
            except: pass

        if not price:
             try:
                meta_price = page.locator('meta[property="product:price:amount"]').first.get_attribute("content")
                if meta_price:
                    print(f"Found meta price: {meta_price}")
                    price = float(meta_price)
             except: pass

        if price:
            print(f"SUCCESS: Found price {price}")
        else:
            print("FAILED: No price found")

    except Exception as e:
        print(f"Error: {e}")
