from typing import Tuple

from src.infrastructure import RedisClient
from src.infrastructure.logger import get_logger
from src.infrastructure.settings import OTPConfig
from src.models import Otp
from src.types import Error
from src.utils import generate_otp_code, hash_otp, make_token

logger = get_logger(__name__)


class OtpUseCase:
    def __init__(self, redis_client: RedisClient, otp_config: OTPConfig) -> None:
        self.__redis_client = redis_client
        self.__otp_config = otp_config

    async def generate_otp(self, user_email: str) -> Tuple[str, str, Error]:
        code = generate_otp_code(self.__otp_config.otp_length)
        hashed_code = hash_otp(code, self.__otp_config.hmac_secret)
        otp = Otp(user_email=user_email, code_hash=hashed_code)
        token = make_token()

        tx = self.__redis_client.transaction()
        tx.create(f"otp:token:{token}", otp)
        tx.create(f"otp:email:{user_email}", token)
        err = await tx.commit()

        if err:
            logger.error("Error saving OTP to redis atomically: %s", err.message())
            return "", "", err
        return code, token, None

    async def verify_otp(self):
        pass

    async def delete_otp(self):
        pass
