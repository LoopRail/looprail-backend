import smtplib
from email.mime.text import MIMEText
from src.infrastructure.logger import get_logger

logger = get_logger(__name__)

# Configure your SMTP credentials here
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = "your_email@gmail.com"
SENDER_PASSWORD = "your_app_password"

def send_email_otp(recipient: str, otp_code: str):
    """
    Sends an OTP to the specified email address.
    """
    message = MIMEText(f"Your verification code is: {otp_code}")
    message["Subject"] = "Your OTP Code"
    message["From"] = SENDER_EMAIL
    message["To"] = recipient

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(message)
            logger.info(f"Sent OTP to {recipient}")
    except Exception as e:
        logger.error(f"Error sending OTP email: {e}")
        raise
