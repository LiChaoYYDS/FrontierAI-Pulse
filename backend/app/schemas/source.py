from datetime import datetime
from pydantic import BaseModel


class SourceResponse(BaseModel):
    id: int
    name: str
    url: str
    type: str
    description: str | None = None
    is_active: bool
    last_fetched: datetime | None = None

    model_config = {"from_attributes": True}
