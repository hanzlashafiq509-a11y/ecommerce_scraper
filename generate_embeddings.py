import sys
import time
from pathlib import Path

import requests


def load_env(path=".env"):
    env = {}
    p = Path(path)
    if not p.exists():
        print(f"ERROR: {path} file nahi mili.")
        sys.exit(1)
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip()
    return env


def get_embedding(text: str, api_key: str):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-001:embedContent?key={api_key}"
    body = {
        "model": "models/gemini-embedding-001",
        "content": {"parts": [{"text": text[:2000]}]},
        "outputDimensionality": 768,
    }
    resp = requests.post(url, json=body, timeout=30)
    if resp.status_code != 200:
        print(f"  Embedding FAILED: {resp.status_code} {resp.text[:200]}")
        return None
    values = resp.json()["embedding"]["values"]
    print(f"    (embedding length: {len(values)})")
    return values


def fetch_products_without_embedding(supabase_url, service_key):
    endpoint = f"{supabase_url}/rest/v1/products"
    headers = {"apikey": service_key, "Authorization": f"Bearer {service_key}"}
    params = {
        "select": "id,name,description,price,currency,rating,stock_status",
        "embedding": "is.null",
    }
    resp = requests.get(endpoint, headers=headers, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def update_embedding(supabase_url, service_key, product_id, embedding):
    endpoint = f"{supabase_url}/rest/v1/products"
    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }
    params = {"id": f"eq.{product_id}"}
    resp = requests.patch(endpoint, headers=headers, params=params,
                           json={"embedding": embedding}, timeout=30)
    if resp.status_code not in (200, 204):
        print(f"    Supabase error {resp.status_code}: {resp.text[:300]}")
        return False
    return True


def main():
    env = load_env()
    supabase_url = env.get("SUPABASE_URL")
    service_key = env.get("SUPABASE_SERVICE_KEY")
    gemini_key = env.get("GEMINI_API_KEY")

    if not gemini_key:
        print("ERROR: .env mein GEMINI_API_KEY nahi mili.")
        sys.exit(1)

    products = fetch_products_without_embedding(supabase_url, service_key)
    print(f"{len(products)} products ke embeddings banane hain...")

    success = 0
    for i, p in enumerate(products, 1):
        text = (
            f"Product: {p.get('name', '')}. "
            f"Price: {p.get('price', '')} {p.get('currency', '')}. "
            f"Rating: {p.get('rating', '')}. "
            f"Stock: {p.get('stock_status', '')}. "
            f"Description: {p.get('description', '')}"
        )
        embedding = get_embedding(text, gemini_key)
        if embedding:
            if update_embedding(supabase_url, service_key, p["id"], embedding):
                success += 1
                print(f"  [{i}/{len(products)}] OK: {p.get('name', '')[:50]}")
            else:
                print(f"  [{i}/{len(products)}] FAILED for id={p['id']}")
        time.sleep(0.3)

    print(f"\n=== Done: {success}/{len(products)} products ka embedding ban gaya ===")


if __name__ == "__main__":
    main()
