import hmac
from typing import Tuple

from src.infrastructure import RedisClient
from src.infrastructure.logger import get_logger
from src.infrastructure.settings import OTPConfig
from src.models import Otp
from src.types import Error, OtpType, error
from src.utils import generate_otp_code, hash_otp, make_token

logger = get_logger(__name__)


class OtpUseCase:
    def __init__(self, redis_client: RedisClient, otp_config: OTPConfig) -> None:
        self.__redis_client = redis_client
        self.__otp_config = otp_config
        logger.debug("OtpUseCase initialized.")

    async def verify_code(self, code: str, otp_hash: str) -> bool:
        """Verify the user-provided OTP code against the stored hash."""
        logger.debug("Verifying OTP code.")
        hashed_code = hash_otp(code, self.__otp_config.hmac_secret)
        is_valid = hmac.compare_digest(hashed_code, otp_hash)
        logger.debug("OTP code verification result: %s", is_valid)
        return is_valid

    async def generate_otp(self, user_email: str) -> Tuple[str, str, Error]:
        logger.debug("Generating OTP for user email: %s", user_email)
        code = generate_otp_code(self.__otp_config.otp_length)
        hashed_code = hash_otp(code, self.__otp_config.hmac_secret)
        otp = Otp(user_email=user_email, code_hash=hashed_code)
        token = make_token()

        tx = await self.__redis_client.transaction()
        await tx.create(f"otp:token:{token}", otp)
        await tx.create(f"otp:email:{user_email}", token)
        err = await tx.commit()

        if err:
            logger.error(
                "Error saving OTP to redis atomically for email %s: %s",
                user_email,
                err.message,
            )
            return "", "", err
        logger.info("OTP generated and saved for user email: %s", user_email)
        return code, token, None

    async def update_otp(self, token, otp: Otp) -> Error:
        logger.debug("Updating OTP for token: %s", token)
        err = await self.__redis_client.update(f"otp:token:{token}", otp)
        if err:
            logger.error("Could not update OTP for token %s: %s", token, err.message)
            return error("Could not update OTP")
        logger.debug("OTP updated for token: %s", token)
        return None

    async def get_user_token(self, user_email) -> Tuple[str, Error]:
        logger.debug("Getting user token for email: %s", user_email)
        key = f"otp:email:{user_email}"
        token, err = await self.__redis_client.get(key)
        if err:
            logger.debug(
                "User token not found for email %s: %s", user_email, err.message
            )
            return "", err
        logger.debug("User token retrieved for email %s", user_email)
        return token, None

    async def get_otp(
        self, token: str, token_type: OtpType
    ) -> Tuple[Otp | None, Error]:
        logger.debug("Getting OTP for token: %s with type: %s", token, token_type)
        key = f"otp:token:{token}"

        otp, err = await self.__redis_client.get(key, Otp)
        if err:
            logger.debug("OTP not found for token %s: %s", token, err.message)
            return None, err
        if otp.otp_type != token_type:
            logger.error(
                "Token type mismatch for token %s: expected %s, got %s",
                token,
                token_type,
                otp.otp_type,
            )
            return None, error("Invald Otp")
        logger.debug("OTP retrieved for token %s", token)
        return otp, None

    async def delete_otp(self, user_email) -> Error:
        logger.debug("Deleting OTP for user email: %s", user_email)
        token, err = await self.get_user_token(user_email)
        if err:
            logger.warning(
                "Could not retrieve token for deleting OTP for user %s: %s",
                user_email,
                err.message,
            )
            return err
        tx = await self.__redis_client.transaction()
        await tx.delete([f"otp:token:{token}"])
        await tx.delete([f"otp:email:{user_email}"])

        err = await tx.commit()

        if err:
            logger.error(
                "Error deleting OTP to redis atomically for email %s: %s",
                user_email,
                err.message,
            )
            return err
        logger.info("OTP deleted for user email: %s", user_email)
        return None
