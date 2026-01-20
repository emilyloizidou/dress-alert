import requests
import time
import os
import sys
import re
import certifi
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

# Ensure TLS uses a valid CA bundle on macOS/venv.
os.environ.setdefault("SSL_CERT_FILE", certifi.where())

load_dotenv()

URL = "https://www.nadinemerabi.com/products/elle-white-dress"
EU_URL = "https://www.eu.nadinemerabi.com/products/elle-white-dress"
TARGET_SIZES = ["S", "S/M", "XL"]

EMAIL = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
TO = os.getenv("TO_EMAIL")

DEBUG = "--debug" in sys.argv
if DEBUG:
    print(f"DEBUG: EMAIL={EMAIL}, TO={TO}")

TEST_MODE = "--test" in sys.argv  # Run once and exit

def _send_email_gmail_smtp(subject: str, body: str) -> None:
    if not EMAIL:
        raise ValueError("EMAIL_ADDRESS is not set")
    if not EMAIL_PASSWORD:
        raise ValueError("EMAIL_PASSWORD is not set")
    if not TO:
        raise ValueError("TO_EMAIL is not set")

    msg = EmailMessage()
    msg["From"] = EMAIL
    msg["To"] = TO
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.ehlo()
        smtp.login(EMAIL, EMAIL_PASSWORD)
        smtp.send_message(msg)


def send_email(size, url):
    subject = "Elle White Dress Available!"
    body = f"🚨 Size {size} is now IN STOCK!\n\nBuy it here:\n{url}"

    try:
        _send_email_gmail_smtp(subject, body)
        print("📧 Email sent (Gmail SMTP)")
    except Exception as e:
        print(f"❌ Gmail SMTP email failed: {e}")

def check_stock():
    print("🔍 Checking stock...")
    found_any = False
    urls = [("UK", URL), ("EU", EU_URL)]
    for region, check_url in urls:
        try:
            r = requests.get(check_url, timeout=20)
            html = r.text
            for size in TARGET_SIZES:
                pattern = f'<input[^>]*name="Size"[^>]*value="{size}"[^>]*>'
                match = re.search(pattern, html)
                if match:
                    input_tag = match.group(0)
                    has_disabled = 'class="disabled"' in input_tag or "class='disabled'" in input_tag
                    if not has_disabled:
                        print(f"✅ Found {size} IN STOCK on {region} site!")
                        send_email(size, check_url)
                        found_any = True
                    else:
                        print(f"  [{region}] {size}: Unavailable")
        except Exception as e:
            print(f"❌ Error checking {region} site: {e}")
    if not found_any:
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
