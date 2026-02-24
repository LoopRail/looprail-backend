import os
from typing import Optional, Tuple
from uuid import uuid4

from email_validator import EmailNotValidError, validate_email
from jinja2 import Environment, FileSystemLoader

from src.types.error import Error, error
from src.types.common_types import ReferenceId
from src.utils.string_utils import camel_case, kebab_case

def get_dir_at_level(level=1, file: str = __file__):
    current_path = os.path.dirname(file)
    if level < 0:
        raise ValueError("Level cannot be less than 0")
    if level == 0:
        return os.path.dirname(file)
    return get_dir_at_level(level - 1, current_path)


def return_base_dir():
    return get_dir_at_level(2)


def return_templates_dir():
    return os.path.join(return_base_dir(), "public", "templates")


def load_html_template(name: str, **kwargs) -> Tuple[Optional[str], Error]:
    templates_dir = return_templates_dir()
    template_path = os.path.join(templates_dir, f"{name}.html")

    if not os.path.exists(template_path):
        return None, error(f"Template not found at {template_path}")

    env = Environment(loader=FileSystemLoader(templates_dir))
    template = env.get_template(f"{name}.html")

    return template.render(**kwargs), None


def is_valid_email(
    email: str,
    disposable_domains: set[str],
) -> bool:
    try:
        # Fast validation: extract domain without DNS networking
        email_info = validate_email(email, check_deliverability=False)
        domain = email_info.domain.lower()
                
        if domain in disposable_domains:
            return False

        return True

    except EmailNotValidError:
        return False


def generate_transaction_reference() -> ReferenceId:
    """Generates a unique transaction reference with a 'ref_' prefix."""
    return f"ref_{uuid4().hex}"
