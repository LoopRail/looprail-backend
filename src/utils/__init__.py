from src.utils.app_utils import (
    get_dir_at_level,
    is_valid_email,
    load_html_template,
    return_base_dir,
)
from src.utils.string_utils import camel_case, kebab_case
from src.utils.auth_utils import (
    compute_pkce_challenge,
    create_refresh_token,
    hash_password,
    validate_password_strength,
    verify_password,
    verify_signature,
)
from src.utils.country_utils import get_country_info, is_valid_country_code
from src.utils.otp_utils import generate_otp_code, hash_otp, make_token
from src.utils.phone_number_utils import validate_and_format_phone_number

# NOTE: Heavy utilities that depend on DTOs/repos are NOT exported via __init__ to avoid circular imports.
# Import them directly from their modules:
# - src.utils.transaction_utils
# - src.utils.notification_helpers
# - src.utils.email_helpers

__all__ = [
    "camel_case",
    "get_dir_at_level",
    "is_valid_email",
    "kebab_case",
    "verify_signature",
    "load_html_template",
    "return_base_dir",
    "generate_otp_code",
    "hash_otp",
    "make_token",
    "is_valid_country_code",
    "get_country_info",
    "validate_and_format_phone_number",
    "verify_password",
    "hash_password",
    "validate_password_strength",
    "create_refresh_token",
    "compute_pkce_challenge",
]
