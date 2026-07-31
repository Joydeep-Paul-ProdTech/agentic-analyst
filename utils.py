import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv()

def send_recovery_email(recipient_email: str, discount_code: str = "15% OFF", cart_id: str = "CART_101") -> bool:
    """Dispatches a real recovery email using Gmail SMTP."""
    sender_email = os.getenv("SENDER_EMAIL")
    sender_password = os.getenv("SENDER_PASSWORD")
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", 587))

    if not sender_email or not sender_password:
        print("❌ Error: Missing SENDER_EMAIL or SENDER_PASSWORD in .env")
        return False

    msg = MIMEMultipart()
    msg['From'] = f"Autonomous Ops Team <{sender_email}>"
    msg['To'] = recipient_email
    msg['Subject'] = f"Action Required: Discount for your cart {cart_id}"

    body = f"""
    Hi,

    We noticed you left items in cart {cart_id}. 
    Here is a special discount to help you complete your order:

    🎁 Code: {discount_code}

    Best,
    E-commerce Operations Team
    """
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        print(f"✅ Email successfully sent to {recipient_email}")
        return True
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        return False