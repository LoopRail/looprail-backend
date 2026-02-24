from typing import Optional, Tuple

import resend
from resend.exceptions import ResendError

from src.infrastructure.settings import ResendConfig, ENVIRONMENT
from src.types import Error, httpError
from src.utils.app_utils import load_html_template
from src.infrastructure.logger import get_logger

logger = get_logger(__name__)

resend.api_key = ""


class ResendService:
    """A service for sending emails via the Resend API."""

    def __init__(self, config: ResendConfig, environment: ENVIRONMENT = ENVIRONMENT.PRODUCTION) -> None:
        """Initializes the ResendService.

        Args:
            config: The Resend configuration.
            environment: The application environment.
        """
        resend.api_key = config.resend_api_key
        self.environment = environment
        self.default_sender_domain = config.default_sender_domain
        logger.debug("ResendService initialized in %s environment with domain %s.", environment.value, self.default_sender_domain)

    async def send(
        self,
        to: str | list[str],
        _from: str,
        subject: str,
        html_content: str | None = None,
        text_content: str | None = None,
    ) -> Tuple[Optional[dict], Error]:
        """Sends an email using the Resend API.

        Args:
            to: The recipient(s) email address(es).
            _from: The sender email address.
            subject: The subject of the email.
            html_content: The HTML content of the email.
            text_content: The plain text content of the email.

        Returns:
            A tuple containing the Resend API response (dict) and an error, if any.
        """
        logger.debug(
            "Attempting to send email to: %s from: %s with subject: %s",
            to,
            _from,
            subject,
        )
        if self.environment == ENVIRONMENT.DEVELOPMENT:
            logger.info(
                "Skipping email send in DEVELOPMENT environment to: %s with subject: %s",
                to,
                subject,
            )
            return {"id": "mock-email-id", "status": "skipped"}, None

        if not html_content and not text_content:
            logger.error(
                "Attempted to send email without html_content or text_content."
            )
            return None, httpError(
                code=400,
                message="Either html_content or text_content must be provided.",
            )

        try:
            # Use the Resend SDK's send method
            response = resend.Emails.send(
                {
                    "from": _from,
                    "to": to if isinstance(to, list) else [to],
                    "subject": subject,
                    "html": html_content,
                    "text": text_content,
                }
            )
            logger.info("Email sent successfully to %s with subject: %s", to, subject)
            return response, None
        except ResendError as e:
            logger.error(
                "Failed to send email to %s with subject %s: %s", to, subject, e
            )
            return None, httpError(code=500, message=f"Failed to send email: {e}")

    async def send_otp(
        self,
        to: str,
        otp_code: str,
        _from: Optional[str] = None,
        subject: str = "Your One-Time Password",
        app_logo_url: Optional[str] = None,
    ) -> Tuple[Optional[dict], Error]:
        """Sends an OTP email.

        Args:
            to: The recipient email address.
            _from: The sender email address.
            otp_code: The OTP code to send.
            subject: The subject of the email.

        Returns:
            A tuple containing the Resend API response (dict) and an error, if any.
        """
        if _from is None:
            if self.default_sender_domain:
                _from = f"noreply@{self.default_sender_domain}"
            else:
                _from = "noreply@looprail.com"  

        logger.debug("Attempting to send OTP email to: %s from: %s", to, _from)
        if self.environment == ENVIRONMENT.DEVELOPMENT:
            logger.info("OTP Code for %s: %s", to, otp_code)
        html_content, err = load_html_template(
            "email/otp_email", 
            otp_code=otp_code,
            app_logo_url=app_logo_url
        )
        if err:
            logger.error("Failed to load OTP email template: %s", err.message)
            return None, err
        text_content = f"Your One-Time Password is: {otp_code}"
        return await self.send(to, _from, subject, html_content, text_content)
