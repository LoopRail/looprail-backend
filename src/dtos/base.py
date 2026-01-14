from pydantic import BaseModel, ConfigDict

from src.utils import kebab_case


class Base(BaseModel):
    model_config = ConfigDict(
        alias_generator=kebab_case, populate_by_name=True, use_enum_values=True
    )
