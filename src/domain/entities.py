from typing import Optional, Callable, List, Dict
from pydantic import BaseModel, ConfigDict, Field, field_validator


class User(BaseModel):
    id: int | None = None
    telegram_id: int = None
    paid: Optional[bool] = False
    paid_minutes: Optional[int] = Field(ge=0, default=0)
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)
    output_formats: List[str] | None = []
    ai_jobs: List[str] | None = []

class QueueElement(BaseModel):
    user_id: int 
    file_path: str
    callback: Callable
    options: Dict[str, List[str]]

