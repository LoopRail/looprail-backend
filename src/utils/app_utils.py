import os


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

