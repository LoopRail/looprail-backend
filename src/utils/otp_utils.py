import hashlib
import hmac
import secrets


def generate_otp_code(length: int) -> str:
    """Generate a numeric OTP of given length, zero-padding if needed."""
    max_num = 10**length
    num = secrets.randbelow(max_num)
    otp = str(num).zfill(length)
    return otp


def hash_otp(otp: str, secret: str) -> str:
    """Return HMAC-SHA256 of the OTP using the server secret."""
    hm = hmac.new(secret.encode("utf-8"), otp.encode("utf-8"), hashlib.sha256)
    return hm.hexdigest()


def make_token() -> str:
    """Generate a random token to identify this OTP session."""
    # 16 bytes → 32 hex characters
    return secrets.token_hex(16)
