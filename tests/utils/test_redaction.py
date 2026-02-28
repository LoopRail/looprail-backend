import pytest
from src.utils.redaction import redact_email, redact_dict, redact_pydantic_errors

def test_redact_email():
    assert redact_email("john.doe@example.com") == "j***e@example.com"
    assert redact_email("a@example.com") == "*@example.com"
    assert redact_email("ab@example.com") == "**@example.com"
    assert redact_email("abc@example.com") == "a***c@example.com"
    assert redact_email(None) is None
    assert redact_email("") == ""

def test_redact_dict():
    data = {
        "email": "test@example.com",
        "password": "secret_password",
        "user": {
            "first_name": "John",
            "pin": "1234"
        },
        "token": "abc-123",
        "items": [
            {"name": "item1", "secret": "shh"},
            {"name": "item2"}
        ]
    }
    redacted = redact_dict(data)
    assert redacted["email"] == "t***t@example.com"
    assert redacted["password"] == "[REDACTED]"
    assert redacted["user"]["pin"] == "[REDACTED]"
    assert redacted["token"] == "[REDACTED]"
    assert redacted["items"][0]["secret"] == "[REDACTED]"
    assert redacted["user"]["first_name"] == "John"
    assert redacted["items"][1]["name"] == "item2"

def test_redact_pydantic_errors():
    errors = [
        {
            "loc": ["body", "password"],
            "msg": "too short",
            "type": "value_error",
            "input": "123"
        },
        {
            "loc": ["body", "email"],
            "msg": "invalid format",
            "type": "value_error",
            "input": "bad-email"
        },
        {
            "loc": ["body", "phone_number"],
            "msg": "missing",
            "type": "value_error",
            "input": {"number": "123"}
        }
    ]
    redacted = redact_pydantic_errors(errors)
    assert redacted[0]["input"] == "[REDACTED]"
    # Email is not redacted here because redact_email returns "bad-email" as is if no @
    assert redacted[1]["input"] == "bad-email"
    
    errors_with_valid_looking_email = [
         {
            "loc": ["body", "email"],
            "msg": "already exists",
            "type": "value_error",
            "input": "john.doe@example.com"
        },
    ]
    redacted_email_err = redact_pydantic_errors(errors_with_valid_looking_email)
    assert redacted_email_err[0]["input"] == "j***e@example.com"
