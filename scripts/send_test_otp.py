import asyncio
import os
import sys

# Ensure the project root is in sys.path
sys.path.append(os.getcwd())

from src.infrastructure.config_settings import load_config
from src.infrastructure.services.resend_service import ResendService
from src.infrastructure.settings import ENVIRONMENT

async def send_test_otp():
    config = load_config()
    
    # Use staging domain for the test if none set in env
    domain = os.getenv("DEFAULT_SENDER_DOMAIN", "staging.looprail.xyz")
    if not config.resend.default_sender_domain:
        config.resend.default_sender_domain = domain
    
    # Force STAGING mode to actually trigger the external API
    service = ResendService(config.resend, environment=ENVIRONMENT.STAGING)
    
    email = ""
    otp_code = "123456"
    
    # We use the full logo if configured
    app_logo_url = config.app.full_logo_url or config.app.logo_url
    
    print(f"Sending test OTP to {email}...")
    print(f"Using Sender Domain: {config.resend.default_sender_domain}")
    print(f"Using Logo URL: {app_logo_url}")
    
    response, err = await service.send_otp(
        to=email,
        otp_code=otp_code,
        subject="LoopRail Test OTP",
        app_logo_url=app_logo_url
    )
    
    if err:
        print(f"Failed to send OTP: {err.message}")
    else:
        print(f"OTP sent successfully! Response: {response}")

if __name__ == "__main__":
    asyncio.run(send_test_otp())
