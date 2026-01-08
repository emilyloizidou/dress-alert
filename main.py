import requests
import time
import os
import sys
import json
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()

URL = "https://www.nadinemerabi.com/products/elle-white-dress"
TARGET_SIZES = ["S", "S/M"]

EMAIL = os.getenv("EMAIL_ADDRESS")
PASSWORD = os.getenv("EMAIL_PASSWORD")
TO = os.getenv("TO_EMAIL")

already_alerted = False
TEST_MODE = "--test" in sys.argv  # Run once and exit

def send_email(size):
    msg = MIMEText(f"🚨 Size {size} is now IN STOCK!\n\nBuy it here:\n{URL}")
    msg["Subject"] = "Elle White Dress Available!"
    msg["From"] = EMAIL
    msg["To"] = TO

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL, PASSWORD)
        server.send_message(msg)

    print("📧 Email sent")

def check_stock():
    global already_alerted

    print("🔍 Checking stock...")
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_default_timeout(60000)
            page.goto(URL, wait_until="domcontentloaded")
            page.wait_for_timeout(1500)  # Wait for JS to render
            
            for size in TARGET_SIZES:
                try:
                    # Find the radio button for this size
                    size_radio = page.locator(f'input[name="Size"][value="{size}"]').first
                    
                    if size_radio.count() > 0:
                        # Check if it has the "disabled" class
                        has_disabled_class = size_radio.evaluate("el => el.classList.contains('disabled')")
                        
                        if not has_disabled_class:
                            # Size is available!
                            if not already_alerted:
                                print(f"✅ Found {size} IN STOCK!")
                                send_email(size)
                                already_alerted = True
                            browser.close()
                            return
                        else:
                            print(f"  {size}: Unavailable")
                except Exception as e:
                    if TEST_MODE:
                        print(f"  Debug: {size} - {e}")
            
            browser.close()
            print("❌ All target sizes still sold out")
    except Exception as e:
        print(f"❌ Error checking stock: {e}")

if TEST_MODE:
    print("🧪 TEST MODE - checking once and exiting...")
    check_stock()
else:
    print("▶️  Starting continuous checker (runs every 30 minutes)")
    while True:
        check_stock()
        print("⏰ Next check in 30 minutes...")
        time.sleep(1800)
