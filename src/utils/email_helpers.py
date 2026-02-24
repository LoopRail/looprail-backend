import os
from src.infrastructure.logger import get_logger
from src.utils.app_utils import load_html_template

logger = get_logger(__name__)

SENDER_EMAIL = os.getenv("SENDER_EMAIL", "notifications@looprail.com")


async def send_transactional_email(
    resend_service,
    to: str,
    subject: str,
    template_name: str,
    app_logo_url: str | None = None,
    **template_vars,
) -> None:
    """
    Fire-and-forget transactional email helper.
    Loads a Jinja2 template, renders it, and sends via ResendService.
    Logs errors but never raises — callers should not block on emails.
    """
    try:
        html_content, err = load_html_template(
            f"email/{template_name}", 
            app_logo_url=app_logo_url,
            **template_vars
        )
        if err:
            logger.error("Failed to load email template '%s': %s", template_name, err)
            return

        _, err = await resend_service.send(
            to=to,
            _from=SENDER_EMAIL,
            subject=subject,
            html_content=html_content,
            text_content=None,
        )
        if err:
            logger.error(
                "Failed to send '%s' email to %s: %s", template_name, to, err
            )
        else:
            logger.info("Sent '%s' email to %s", template_name, to)
    except Exception as e:
        logger.error(
            "Unexpected error sending '%s' email to %s: %s", template_name, to, e
        )
