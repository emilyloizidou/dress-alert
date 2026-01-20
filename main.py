import requests
import time
import os
import sys
import re
import certifi
import smtplib
import socket
from email.message import EmailMessage
from typing import Optional
try:
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail
except Exception:  # sendgrid is optional (e.g. local SMTP-only installs)
    SendGridAPIClient = None
    Mail = None
from dotenv import load_dotenv
# small change

# Ensure TLS uses a valid CA bundle on macOS/venv.
os.environ.setdefault("SSL_CERT_FILE", certifi.where())

load_dotenv()

URL = "https://www.nadinemerabi.com/products/elle-white-dress"
EU_URL = "https://www.eu.nadinemerabi.com/products/elle-white-dress"
TARGET_SIZES = ["S", "S/M"]

EMAIL = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
TO = os.getenv("TO_EMAIL")
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
SENDGRID_FROM_EMAIL = os.getenv("SENDGRID_FROM_EMAIL") or EMAIL


DEBUG = "--debug" in sys.argv
if DEBUG:
    print(
        f"DEBUG: EMAIL={EMAIL}, TO={TO}, SENDGRID_API_KEY={'set' if SENDGRID_API_KEY else 'None'}, "
        f"SENDGRID_FROM_EMAIL={SENDGRID_FROM_EMAIL}",
        flush=True,
    )

TEST_MODE = "--test" in sys.argv  # Run once and exit


def log(message: str) -> None:
    print(message, flush=True)


def _smtp_connectivity_check(host: str, port: int, timeout_seconds: int = 5) -> None:
    try:
        with socket.create_connection((host, port), timeout=timeout_seconds):
            return
    except OSError as e:
        raise ConnectionError(
            f"Cannot connect to SMTP server {host}:{port}. Many hosts (including Railway) block outbound SMTP. "
            f"Use an email HTTP API provider (e.g. SendGrid) or an allowed SMTP relay. Underlying error: {e}"
        )

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

    host = "smtp.gmail.com"
    port = 587
    _smtp_connectivity_check(host, port, timeout_seconds=5)

    log("📨 Connecting to Gmail SMTP...")
    with smtplib.SMTP(host, port, timeout=15) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.ehlo()
        smtp.login(EMAIL, EMAIL_PASSWORD)
        smtp.send_message(msg)


def _send_email_sendgrid(subject: str, body: str) -> None:
    if not SENDGRID_API_KEY:
        raise ValueError("SENDGRID_API_KEY is not set")
    if SendGridAPIClient is None or Mail is None:
        raise RuntimeError("sendgrid package is not installed")
    if not TO:
        raise ValueError("TO_EMAIL is not set")
    if not SENDGRID_FROM_EMAIL:
        raise ValueError("SENDGRID_FROM_EMAIL/EMAIL_ADDRESS is not set")

    message = Mail(
        from_email=SENDGRID_FROM_EMAIL,
        to_emails=TO,
        subject=subject,
        plain_text_content=body,
    )
    sg = SendGridAPIClient(SENDGRID_API_KEY)
    sg.send(message)


def send_email(size, url):
    subject = "Elle White Dress Available!"
    body = f"🚨 Size {size} is now IN STOCK!\n\nBuy it here:\n{url}"

    try:
        if SENDGRID_API_KEY:
            _send_email_sendgrid(subject, body)
            log("📧 Email sent (SendGrid)")
            return

        _send_email_gmail_smtp(subject, body)
        log("📧 Email sent (Gmail SMTP)")
    except Exception as e:
        provider = "SendGrid" if SENDGRID_API_KEY else "Gmail SMTP"
        details = ""
        for attr in ("body", "message"):
            val = getattr(e, attr, None)
            if val:
                try:
                    details = val.decode("utf-8", errors="replace") if isinstance(val, (bytes, bytearray)) else str(val)
                except Exception:
                    details = str(val)
                break

        if details:
            log(f"❌ {provider} email failed: {e}\n--- details ---\n{details}\n-------------")
        else:
            log(f"❌ {provider} email failed: {e}")

def check_stock():
    log("🔍 Checking stock...")
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
                        log(f"  [{region}] {size}: Unavailable")
        except Exception as e:
            log(f"❌ Error checking {region} site: {e}")
    if not found_any:
        log("❌ All target sizes still sold out on both sites")

if TEST_MODE:
    log("🧪 TEST MODE - checking once and exiting...")
    check_stock()
else:
    log("▶️  Starting continuous checker (runs every 30 minutes)")
    while True:
        check_stock()
        log("⏰ Next check in 30 minutes...")
        time.sleep(1800)
