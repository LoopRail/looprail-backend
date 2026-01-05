import re
from typing import Optional

from src.types import error


def validate_password_strength(password: str) -> Optional[error]:
    """
    Validates the strength of a password based on the following rules:
    - Minimum 8 characters.
    - Maximum 64 characters.
    - At least one uppercase letter.
    - At least one lowercase letter.
    - At least one digit.
    - At least one special character from the set [@, #, $, %, ^, &, +, = or !].
    """
    if not (8 <= len(password) <= 64):
        return error("Password must be between 8 and 64 characters long.")
    if not re.search(r"[a-z]", password):
        return error("Password must contain at least one lowercase letter.")
    if not re.search(r"[A-Z]", password):
        return error("Password must contain at least one uppercase letter.")
    if not re.search(r"\d", password):
        return error("Password must contain at least one digit.")
    if not re.search(r"[@#$%^&+=!]", password):
        return error("Password must contain at least one special character (@, #, $, %, ^, &, +, = or !).")
    return None
