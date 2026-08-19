import re
import os
import sys
from pathlib import Path

import requests
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


def load_env(path=".env"):
    # Pehle real environment variables check karo (live server jaise Render pe yahi milte hain)
    env_keys = ["SUPABASE_URL", "SUPABASE_SERVICE_KEY", "GEMINI_API_KEY"]
    if all(os.environ.get(k) for k in env_keys):
        return {k: os.environ[k] for k in env_keys}
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


ENV = load_env()
SUPABASE_URL = ENV["SUPABASE_URL"]
SUPABASE_KEY = ENV["SUPABASE_SERVICE_KEY"]
GEMINI_KEY = ENV["GEMINI_API_KEY"]

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class HistoryItem(BaseModel):
    role: str
    text: str


class ChatRequest(BaseModel):
    message: str
    history: list[HistoryItem] = []
    language: str = "en"
    intent: str = "product"


def call_gemini(prompt: str, retries: int = 2):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent?key={GEMINI_KEY}"
    body = {"contents": [{"parts": [{"text": prompt}]}]}
    last_err = None
    for _ in range(retries):
        try:
            resp = requests.post(url, json=body, timeout=20)
            resp.raise_for_status()
            data = resp.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            last_err = e
    raise last_err


def structured_search(keyword: str = None, max_price: float = None, limit: int = 8):
    endpoint = f"{SUPABASE_URL}/rest/v1/products"
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
    params = {"select": "*", "limit": str(limit), "order": "price.asc"}
    if keyword:
        params["name"] = f"ilike.*{keyword}*"
    if max_price:
        params["price"] = f"lte.{max_price}"
    resp = requests.get(endpoint, headers=headers, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def get_real_categories():
    endpoint = f"{SUPABASE_URL}/rest/v1/products"
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
    resp = requests.get(endpoint, headers=headers, params={"select": "name", "limit": "150"}, timeout=30)
    resp.raise_for_status()
    names = [p.get("name", "") for p in resp.json()]
    known_words = ["shirt", "trouser", "jeans", "polo", "watch", "jacket", "blazer",
                    "shade", "glasses", "perfume", "bracelet", "shoe", "sneaker",
                    "boot", "loafer", "tracksuit", "co-ord", "slide", "coat", "denim"]
    found = set()
    for name in names:
        low = name.lower()
        for w in known_words:
            if w in low:
                found.add(w + "s" if not w.endswith("s") else w)
    return sorted(found) if found else ["shirts", "trousers", "watches"]


REAL_CATEGORIES = get_real_categories()
CATEGORIES_STR = ", ".join(REAL_CATEGORIES)

OPEN_BUDGET_PHRASES = ["open budget", "koi budget nahi", "budget nahi", "no budget",
                        "unlimited", "kuch bhi chalega", "matter nahi karta", "important nahi"]

FAQ_WORDS = ["cash on delivery", " cod", "delivery", "shipping", "return", "policy",
             "warranty", "exchange", "payment", "refund", "kitne din", "how long",
             "kahan", "location", "address", "timing", "khula", "band"]

PRODUCT_INTENT_WORDS = ["chahiye", "dikhao", "milta", "milti", "bechte", "bechty",
                         "sell", "available", "hai kya", "rakhtay", "rakhte", "want",
                         "need", "looking for", "have", "k pass", "ke pass", "kay pass",
                         "paas", "milega", "milegi", "stock mein", "stock me", "hota hai"]


def find_category(text: str):
    t = text.lower()
    for cat in REAL_CATEGORIES:
        singular = cat.rstrip("s")
        if cat in t or singular in t:
            return cat
    return None


def find_budget(text: str):
    t = text.replace(",", "")
    m = re.search(r"(\d{3,7})", t)
    return int(m.group(1)) if m else None


def is_open_budget(text: str):
    t = text.lower()
    return any(p in t for p in OPEN_BUDGET_PHRASES)


def looks_like_faq(text: str):
    t = text.lower()
    return any(w in t for w in FAQ_WORDS)


def looks_like_product_request(text: str):
    t = text.lower()
    return any(w in t for w in PRODUCT_INTENT_WORDS)


def analyze_fast(history, message):
    user_turns = [h.text for h in history if h.role == "user"] + [message]

    running_category = None
    category_budgets = {}
    open_categories = set()

    for text in user_turns:
        cat = find_category(text)
        if cat:
            running_category = cat
        elif looks_like_faq(text):
            running_category = None
        if running_category:
            if is_open_budget(text):
                open_categories.add(running_category)
            budget = find_budget(text)
            if budget:
                category_budgets[running_category] = budget
                open_categories.discard(running_category)

    msg_category = find_category(message)
    msg_is_faq = looks_like_faq(message)
    msg_is_unavailable = (msg_category is None and not msg_is_faq and looks_like_product_request(message))

    return running_category, category_budgets, open_categories, msg_is_faq, msg_is_unavailable


NO_FAKE_ORDER_RULE = (
    "ZAROORI: Tum khud order place ya 'note' NAHI kar sakte - tum sirf product dikhate ho. "
    "Agar customer kahe 'ye order kardo' ya 'ye lena hai', to unhe politely batayein ke upar diye gaye "
    "link par click karke website se order complete karein - kabhi ye mat kahiye ke order note/save ho gaya."
)

NO_MARKDOWN_RULE = "Kabhi bhi markdown link format [text](url) ya numbered footnote links use na karein - agar link dena hai to sirf plain URL likhein."


@app.post("/chat")
def chat(req: ChatRequest):
    message = req.message
    history = req.history
    is_first = len(history) == 0
    lang_instruction = "Respond ONLY in clear English." if req.language == "en" else "Sirf Roman Urdu mein jawab dein (Hindi lafz ya Devanagari kabhi nahi)."

    current_category, category_budgets, open_categories, msg_is_faq, msg_is_unavailable = analyze_fast(history, message)

    name_instruction = (
        "Ye customer ka pehla message hai - shuru mein 'Hanzla Creation' ka intro dein."
        if is_first else
        "Naam/intro dobara mat dein, seedha jawab dein."
    )

    if msg_is_unavailable:
        prompt = f"""Tum 'Hanzla Creation' ke chatbot ho. Customer ne kuch aisa maanga jo humari dukaan mein NAHI hai: "{message}"
{name_instruction}
Hamari dukaan mein sirf ye milta hai: {CATEGORIES_STR}

HIDAYAT: {lang_instruction} {NO_FAKE_ORDER_RULE} Chota (2 line) maazrat ke sath batayein ye available nahi, aur 3-4 asli categories suggest karein."""
        reply = call_gemini(prompt)
        return {"reply": reply, "products": [], "show_links": False}

    if msg_is_faq or (not current_category and req.intent == "info"):
        prompt = f"""Tum 'Hanzla Creation' ke helpful chatbot ho. Customer ne general/policy sawaal poocha: "{message}"
{name_instruction}

HIDAYAT: {lang_instruction} {NO_FAKE_ORDER_RULE} Chota jawab (2-3 line). Agar exact policy info nahi pata, honestly batayein aur website/support check karne ka bolein - khud se policy mat banayein."""
        reply = call_gemini(prompt)
        return {"reply": reply, "products": [], "show_links": False}

    if req.intent == "info" and not current_category:
        prompt = f"""Tum 'Hanzla Creation' ke helpful chatbot ho. Customer ne kaha: "{message}"
{name_instruction}
Hamari dukaan mein ye milta hai: {CATEGORIES_STR}

HIDAYAT: {lang_instruction} {NO_FAKE_ORDER_RULE} Chota, madadgar jawab dein."""
        reply = call_gemini(prompt)
        return {"reply": reply, "products": [], "show_links": False}

    if not current_category:
        prompt = f"""Tum 'Hanzla Creation' ke friendly Pakistani e-commerce chatbot ho.
Customer ne kaha: "{message}"
{name_instruction}
Hamari dukaan mein ye cheezein hain: {CATEGORIES_STR}

HIDAYAT: {lang_instruction} {NO_FAKE_ORDER_RULE} Chota jawab (2-3 line), koi link nahi, poochein unhe kis cheez mein dilchaspi hai (sirf upar wali list se)."""
        reply = call_gemini(prompt)
        return {"reply": reply, "products": [], "show_links": False}

    budget = category_budgets.get(current_category)
    is_open = current_category in open_categories

    if budget or is_open:
        products = structured_search(keyword=current_category.rstrip("s"), max_price=budget, limit=8)

        if not products:
            prompt = f"""Tum 'Hanzla Creation' ke chatbot ho. Customer ne "{current_category}" ke liye Rs.{budget} budget bataya, lekin koi product nahi mila.
{name_instruction}
HIDAYAT: {lang_instruction} Chota (2 line) maazrat ke sath bataein aur budget barhane ka suggest karein."""
            reply = call_gemini(prompt)
            return {"reply": reply, "products": [], "show_links": False}

        budget_line = f'"{current_category}" ke liye Rs.{budget} budget mein' if budget else f'"{current_category}" mein (open budget)'

        prompt = f"""Tum 'Hanzla Creation' ke chatbot ho. {budget_line} {len(products)} products mile hain.
{name_instruction}

HIDAYAT: {lang_instruction} {NO_FAKE_ORDER_RULE} {NO_MARKDOWN_RULE}
Sirf EK CHOTA jawab dein (maximum 2 lines) - jaise "Rs.{budget or "open"} budget mein aapke liye {len(products)} shirts hain, neeche dekh lein!"
Product ke NAAM, PRICE, ya LINK bilkul TEXT mein mat likhein - wo sab neeche cards mein pehle se dikh raha hai. Sirf ek chota, friendly line likhein."""
        reply = call_gemini(prompt)
        return {"reply": reply, "products": products, "show_links": True}

    products = structured_search(keyword=current_category.rstrip("s"), limit=6)
    products_text = "\n".join(f"- {p.get('name')} | Price: {p.get('price')}" for p in products) or "Stock check kar rahe hain."

    prompt = f"""Tum 'Hanzla Creation' ke chatbot ho. Customer "{current_category}" mein dilchaspi rakhta hai.
{name_instruction}
Available: {products_text}

HIDAYAT: {lang_instruction} {NO_FAKE_ORDER_RULE} {NO_MARKDOWN_RULE} Sirf naam aur price dein, LINK mat dein. Agar "best-selling"/"popular" poocha hai to honestly batayein sales-data track nahi karte. Aakhir mein "{current_category}" ke liye budget poochein (ya 'open budget' bata sakte hain)."""
    reply = call_gemini(prompt)
    return {"reply": reply, "products": [], "show_links": False}


@app.get("/")
def health():
    return {"status": "Chatbot backend chal raha hai"}
