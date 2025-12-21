import os
from typing import Optional, Tuple

from jinja2 import Environment, FileSystemLoader

from src.types.error import Error, error


def get_dir_at_level(level=1, file: str = __file__):
    current_path = os.path.dirname(file)
    if level < 0:
        raise ValueError("Level cannot be less than 0")
    if level == 0:
        return os.path.dirname(file)
    return get_dir_at_level(level - 1, current_path)


def return_base_dir():
    return get_dir_at_level(2)


def kebab_case(s: str) -> str:
    return s.replace("_", "-")


def camel_case(s: str) -> str:
    parts = s.split("_")
    return parts[0] + "".join(word.capitalize() for word in parts[1:])


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
