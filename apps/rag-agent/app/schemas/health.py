from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str  # ok, error, unavailable
    service: str
    detail: str = ""
    timestamp: Optional[datetime] = None


class HealthSummary(BaseModel):
    status: str
    services: dict[str, HealthResponse]
