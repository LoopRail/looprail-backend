from typing import Optional, Tuple

from resend import Resend
from resend.exceptions import ResendError

from src.infrastructure.settings import ResendConfig
from src.types import Error, httpError


class ResendService:
    """A service for sending emails via the Resend API."""

    def __init__(self, config: ResendConfig) -> None:
        """Initializes the ResendService.

        Args:s
            config: The Resend configuration.
        """
        self.config = config
        self._resend_client = Resend(api_key=config.resend_api_key)

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
        if not html_content and not text_content:
            return None, httpError(
                code=400,
                message="Either html_content or text_content must be provided.",
            )

        try:
            # Use the Resend SDK's send method
            response = self._resend_client.emails.send(
                {
                    "from": _from,
                    "to": to if isinstance(to, list) else [to],
                    "subject": subject,
                    "html": html_content,
                    "text": text_content,
                }
            )
            # The Resend SDK returns a dict on success, or raises an exception on error.
            return response, None
        except ResendError as e:
            return None, httpError(code=500, message=f"Failed to send email: {e}")

    async def send_otp(
        self,
        to: str,
        _from: str,
        otp_code: str,
        subject: str = "Your One-Time Password",
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
        html_content = f"<p>Your One-Time Password is: <strong>{otp_code}</strong></p>"
        text_content = f"Your One-Time Password is: {otp_code}"
        return await self.send(to, _from, subject, html_content, text_content)

