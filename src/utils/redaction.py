import re
from typing import Any, Dict, List, Union

SENSITIVE_KEYS = {
    "password",
    "pin",
    "transaction_pin",
    "token",
    "refresh_token",
    "access_token",
    "fcm_token",
    "code",
    "code_hash",
    "sub",
    "secret",
    "signature",
    "authorization",
}


def redact_email(email: str) -> str:
    """
    Redacts an email address, e.g., 'john.doe@example.com' -> 'j***e@example.com'
    """
    if not email or "@" not in email:
        return email

    try:
        local_part, domain = email.split("@")
        if len(local_part) <= 2:
            redacted_local = "*" * len(local_part)
        else:
            redacted_local = local_part[0] + "***" + local_part[-1]
        return f"{redacted_local}@{domain}"
    except Exception:
        return "[REDACTED EMAIL]"


def redact_value(key: str, value: Any) -> Any:
    """
    Redacts a value if the key is sensitive.
    """
    if not isinstance(key, str):
        return value

    key_lower = key.lower()
    
    # Check if key is sensitive
    if any(sk in key_lower for sk in SENSITIVE_KEYS):
        return "[REDACTED]"
    
    # Special handling for emails even if key doesn't match sensitive keys (extra safety)
    if isinstance(value, str) and "@" in value and ("email" in key_lower or "user" in key_lower):
        return redact_email(value)
        
    return value


def redact_dict(data: Union[Dict, List, Any]) -> Any:
    """
    Recursively redacts sensitive keys in a dictionary or list.
    """
    if isinstance(data, dict):
        return {k: redact_dict(redact_value(k, v)) if not isinstance(v, (dict, list)) else redact_dict(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [redact_dict(item) for item in data]
    return data


def redact_pydantic_errors(errors: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Redacts Pydantic error details.
    """
    redacted_errors = []
    for error in errors:
        new_error = error.copy()
        
        # Redact the location path if it contains sensitive keys
        loc = new_error.get("loc", [])
        is_sensitive_loc = False
        for part in loc:
            if isinstance(part, str) and any(sk in part.lower() for sk in SENSITIVE_KEYS):
                is_sensitive_loc = True
                break
        
        # Redact input value if present
        if "input" in new_error:
            if is_sensitive_loc:
                new_error["input"] = "[REDACTED]"
            elif isinstance(new_error["input"], str) and "@" in new_error["input"]:
                # Probable email
                new_error["input"] = redact_email(new_error["input"])
            elif isinstance(new_error["input"], (dict, list)):
                new_error["input"] = redact_dict(new_error["input"])

        # Also redact 'ctx' if it exists and contains sensitive values
        if "ctx" in new_error and isinstance(new_error["ctx"], dict):
            new_error["ctx"] = redact_dict(new_error["ctx"])

        redacted_errors.append(new_error)
    return redacted_errors
