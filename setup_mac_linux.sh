#!/bin/bash
echo "=== Step 1: Installing Python packages ==="
pip3 install -r requirements.txt --break-system-packages

echo ""
echo "=== Step 2: Installing Playwright browser ==="
playwright install chromium

echo ""
echo "=== Setup complete! ==="
echo "Ab is folder mein terminal khol ke ye likho:"
echo "python3 generic_ecommerce_scraper.py \"https://client-website-url.com\""
