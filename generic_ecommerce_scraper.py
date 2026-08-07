"""
Generic E-commerce Scraper
===========================
Kisi bhi e-commerce website se product data nikalne ke liye.
3-layer strategy try karta hai (jo pehle kaam kare, wahi use hota hai):

  Layer 1 -> Shopify /products.json  ya  WooCommerce REST API
  Layer 2 -> schema.org JSON-LD (application/ld+json) - universal, SEO ke liye
             almost har modern e-commerce site pe hota hai
  Layer 3 -> Generic HTML scraping (Playwright) - last resort fallback

USAGE:
    pip install playwright requests --break-system-packages
    playwright install chromium

    python generic_ecommerce_scraper.py "https://example-store.com"

OUTPUT:
    ek structured JSON file: output/<domain>_products.json
    Har product mein: name, price, currency, rating, stock_status, url, image, description
"""

import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from playwright.sync_api import sync_playwright

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
}


# ---------------------------------------------------------------------------
# LAYER 1a: Shopify detection + native JSON export
# ---------------------------------------------------------------------------
def try_shopify(base_url: str):
    """Har Shopify store /products.json pe public structured data deta hai."""
    url = urljoin(base_url, "/products.json")
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10, params={"limit": 250})
        if resp.status_code != 200:
            return None
        data = resp.json()
        products = data.get("products")
        if not products:
            return None

        results = []
        for p in products:
            variant = (p.get("variants") or [{}])[0]
            image = (p.get("images") or [{}])[0].get("src")
            results.append({
                "name": p.get("title"),
                "price": variant.get("price"),
                "currency": None,  # Shopify JSON doesn't include currency; fetch from store meta if needed
                "rating": None,
                "stock_status": "in_stock" if variant.get("available") else "out_of_stock",
                "url": urljoin(base_url, f"/products/{p.get('handle')}"),
                "image": image,
                "description": re.sub("<[^<]+?>", "", p.get("body_html") or "").strip()[:500],
                "source": "shopify_json",
            })
        print(f"[Shopify] {len(results)} products mil gaye seedha JSON se.")
        return results
    except Exception:
        return None


# ---------------------------------------------------------------------------
# LAYER 1b: WooCommerce detection (needs API key for full REST API, so we
# fall back to trying the public store REST endpoint used by some themes)
# ---------------------------------------------------------------------------
def try_woocommerce(base_url: str):
    """
    Full WooCommerce REST API ke liye client ki consumer key/secret chahiye
    (WP Admin -> WooCommerce -> Settings -> Advanced -> REST API se milegi).
    Agar available ho to yahan daal do. Warna ye function skip ho jayega
    aur Layer 2 (JSON-LD) try hoga.
    """
    consumer_key = None     # <-- client se lekar yahan daalna
    consumer_secret = None  # <-- client se lekar yahan daalna

    if not consumer_key or not consumer_secret:
        return None

    url = urljoin(base_url, "/wp-json/wc/v3/products")
    try:
        resp = requests.get(
            url, headers=HEADERS, timeout=10,
            params={"per_page": 100, "consumer_key": consumer_key, "consumer_secret": consumer_secret},
        )
        if resp.status_code != 200:
            return None
        products = resp.json()
        results = []
        for p in products:
            results.append({
                "name": p.get("name"),
                "price": p.get("price"),
                "currency": None,
                "rating": p.get("average_rating"),
                "stock_status": p.get("stock_status"),
                "url": p.get("permalink"),
                "image": (p.get("images") or [{}])[0].get("src"),
                "description": re.sub("<[^<]+?>", "", p.get("short_description") or "").strip()[:500],
                "source": "woocommerce_api",
            })
        print(f"[WooCommerce] {len(results)} products mil gaye REST API se.")
        return results
    except Exception:
        return None


# ---------------------------------------------------------------------------
# LAYER 2: schema.org JSON-LD - universal fallback for individual product pages
# ---------------------------------------------------------------------------
def extract_jsonld_product(html: str, page_url: str):
    """Ek product page ke HTML se schema.org Product JSON-LD nikalta hai."""
    matches = re.findall(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html, re.DOTALL | re.IGNORECASE,
    )
    for raw in matches:
        try:
            data = json.loads(raw.strip())
        except Exception:
            continue

        candidates = data if isinstance(data, list) else [data]
        for item in candidates:
            if isinstance(item, dict) and "@graph" in item:
                candidates.extend(item["@graph"])
            if isinstance(item, dict) and item.get("@type") in ("Product", ["Product"]):
                offers = item.get("offers") or {}
                if isinstance(offers, list):
                    offers = offers[0] if offers else {}
                agg_rating = item.get("aggregateRating") or {}
                return {
                    "name": item.get("name"),
                    "price": offers.get("price"),
                    "currency": offers.get("priceCurrency"),
                    "rating": agg_rating.get("ratingValue"),
                    "stock_status": (offers.get("availability") or "").split("/")[-1] or None,
                    "url": page_url,
                    "image": item.get("image") if isinstance(item.get("image"), str)
                             else (item.get("image") or [None])[0],
                    "description": (item.get("description") or "")[:500],
                    "source": "jsonld",
                }
    return None


# ---------------------------------------------------------------------------
# LAYER 3: Generic Playwright fallback - discover product links + scrape each
# ---------------------------------------------------------------------------
def discover_product_links(page, base_url: str, max_links: int = 60):
    """Homepage/category pages se product-jaisi lagti links dhoondta hai."""
    hrefs = page.eval_on_selector_all("a", "els => els.map(e => e.href)")
    keywords = ["/product", "/products/", "/item", "/p/", "/shop/"]
    links = set()
    for h in hrefs:
        if not h:
            continue
        if urlparse(h).netloc != urlparse(base_url).netloc:
            continue
        if any(k in h.lower() for k in keywords):
            links.add(h.split("?")[0])
    return list(links)[:max_links]


def generic_scrape(base_url: str, max_products: int = 60):
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent=HEADERS["User-Agent"])

        print("[Generic] Homepage khol rahe hain, product links dhoond rahe hain...")
        page.goto(base_url, timeout=30000, wait_until="domcontentloaded")
        product_links = discover_product_links(page, base_url, max_products)

        if not product_links:
            print("[Generic] Koi product link nahi mila homepage se. Manual selector chahiye hoga.")
            browser.close()
            return results

        print(f"[Generic] {len(product_links)} product pages milein. Scrape kar rahe hain...")
        for link in product_links:
            try:
                page.goto(link, timeout=20000, wait_until="domcontentloaded")
                html = page.content()
                product = extract_jsonld_product(html, link)
                if product:
                    results.append(product)
                time.sleep(0.5)  # polite delay - website pe load kam daalne ke liye
            except Exception as e:
                print(f"  -> skip {link}: {e}")

        browser.close()
    return results


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def scrape_store(base_url: str):
    if not base_url.startswith("http"):
        base_url = "https://" + base_url

    print(f"\n=== Scraping start: {base_url} ===")

    products = try_shopify(base_url)
    if products:
        return products

    products = try_woocommerce(base_url)
    if products:
        return products

    print("[Info] Shopify/WooCommerce nahi mila -> generic JSON-LD scraping try kar rahe hain.")
    products = generic_scrape(base_url)
    return products


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python generic_ecommerce_scraper.py <store_url>")
        sys.exit(1)

    store_url = sys.argv[1]
    products = scrape_store(store_url)

    domain = urlparse(store_url if store_url.startswith("http") else "https://" + store_url).netloc
    domain = domain.replace("www.", "").replace(".", "_")
    out_path = OUTPUT_DIR / f"{domain}_products.json"

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)

    print(f"\n=== Done: {len(products)} products saved -> {out_path} ===")
