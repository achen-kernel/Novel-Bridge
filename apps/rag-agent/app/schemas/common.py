from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class CommonResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: Any = None
