import requests
import time
import os
import sys
import re
from email.mime.text import MIMEText
import smtplib
from dotenv import load_dotenv

load_dotenv()

URL = "https://www.nadinemerabi.com/products/elle-white-dress"
EU_URL = "https://www.eu.nadinemerabi.com/products/elle-white-dress"
TARGET_SIZES = ["S", "S/M", "XL"]

EMAIL = os.getenv("EMAIL_ADDRESS")
PASSWORD = os.getenv("EMAIL_PASSWORD")
TO = os.getenv("TO_EMAIL")

TEST_MODE = "--test" in sys.argv  # Run once and exit

def send_email(size, url):
    msg = MIMEText(f"🚨 Size {size} is now IN STOCK!\n\nBuy it here:\n{url}")
    msg["Subject"] = "Elle White Dress Available!"
    msg["From"] = EMAIL
    msg["To"] = TO

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL, PASSWORD)
        server.send_message(msg)

    print("📧 Email sent")

def check_stock():
    print("🔍 Checking stock...")
    
    urls = [("UK", URL), ("EU", EU_URL)]
    
    for region, check_url in urls:
        try:
            r = requests.get(check_url, timeout=20)
            html = r.text
            
            for size in TARGET_SIZES:
                # Look for the pattern: <input ... name="Size" value="S" ... class="disabled">
                # If it has class="disabled", it's unavailable. If no class="disabled", it's available
                
                pattern = f'<input[^>]*name="Size"[^>]*value="{size}"[^>]*>'
                match = re.search(pattern, html)
                
                if match:
                    input_tag = match.group(0)
                    has_disabled = 'class="disabled"' in input_tag or "class='disabled'" in input_tag
                    
                    if not has_disabled:
                        # Size is available!
                        print(f"✅ Found {size} IN STOCK on {region} site!")
                        send_email(size, check_url)
                    else:
                        print(f"  [{region}] {size}: Unavailable")
        except Exception as e:
            print(f"❌ Error checking {region} site: {e}")
    
    print("❌ All target sizes still sold out on both sites")

if TEST_MODE:
    print("🧪 TEST MODE - checking once and exiting...")
    check_stock()
else:
    print("▶️  Starting continuous checker (runs every 30 minutes)")
    while True:
        check_stock()
        print("⏰ Next check in 30 minutes...")
        time.sleep(1800)
