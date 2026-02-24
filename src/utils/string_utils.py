def kebab_case(s: str) -> str:
    return s.replace("_", "-")


def camel_case(s: str) -> str:
    parts = s.split("_")
    return parts[0] + "".join(word.capitalize() for word in parts[1:])
