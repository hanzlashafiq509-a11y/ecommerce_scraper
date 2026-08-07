@echo off
echo === Step 1: Installing Python packages ===
pip install -r requirements.txt --break-system-packages

echo.
echo === Step 2: Installing Playwright browser ===
playwright install chromium

echo.
echo === Setup complete! ===
echo Ab is folder mein terminal khol ke ye likho:
echo python generic_ecommerce_scraper.py "https://client-website-url.com"
pause
