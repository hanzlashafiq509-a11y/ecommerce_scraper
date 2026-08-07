import glob
import json
import sys
from pathlib import Path

import requests


def load_env(path=".env"):
    env = {}
    p = Path(path)
    if not p.exists():
        print(f"ERROR: {path} file nahi mili. Pehle .env banao (SUPABASE_URL aur SUPABASE_SERVICE_KEY ke saath).")
        sys.exit(1)
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip()
    return env


def find_products_json():
    files = glob.glob("output/*_products.json")
    if not files:
        print("ERROR: output/ folder mein koi *_products.json file nahi mili. Pehle scraper chalao.")
        sys.exit(1)
    return files[0]


def upload(env, json_path):
    supabase_url = env.get("SUPABASE_URL")
    service_key = env.get("SUPABASE_SERVICE_KEY")

    if not supabase_url or not service_key or "yahan_apni" in service_key:
        print("ERROR: .env file mein SUPABASE_URL aur SUPABASE_SERVICE_KEY sahi se bhare nahi lag rahe.")
        sys.exit(1)

    with open(json_path, encoding="utf-8") as f:
        products = json.load(f)

    if not products:
        print("JSON file khaali hai, kuch upload nahi hoga.")
        return

    rows = []
    for p in products:
        rows.append({
            "name": p.get("name"),
            "price": p.get("price"),
            "currency": p.get("currency"),
            "rating": p.get("rating"),
            "stock_status": p.get("stock_status"),
            "product_url": p.get("url"),
            "image": p.get("image"),
            "description": p.get("description"),
            "source": p.get("source"),
        })

    endpoint = f"{supabase_url}/rest/v1/products"
    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=minimal",
    }

    params = {"on_conflict": "product_url"}

    batch_size = 50
    total = len(rows)
    for i in range(0, total, batch_size):
        batch = rows[i:i + batch_size]
        resp = requests.post(endpoint, headers=headers, params=params, json=batch, timeout=30)
        if resp.status_code not in (200, 201, 204):
            print(f"  -> Batch {i}-{i+len(batch)} FAILED ({resp.status_code}): {resp.text[:300]}")
        else:
            print(f"  -> Batch {i}-{i+len(batch)} uploaded ({len(batch)} products)")

    print(f"\n=== Done: {total} products Supabase mein upload/update ho gaye ===")


if __name__ == "__main__":
    env = load_env()
    json_path = sys.argv[1] if len(sys.argv) > 1 else find_products_json()
    print(f"Uploading: {json_path}")
    upload(env, json_path)
