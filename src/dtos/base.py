from typing import Any, ClassVar
from pydantic import BaseModel, ConfigDict

from src.utils.string_utils import kebab_case


class Base(BaseModel):
    dto_config: ClassVar[Any] = None
    model_config = ConfigDict(
        alias_generator=kebab_case,
        populate_by_name=True,
        use_enum_values=True,
        arbitrary_types_allowed=True,
        from_attributes=True,
    )
