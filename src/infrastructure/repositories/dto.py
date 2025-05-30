from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from src.domain.entities import User

class UserAddDTO(BaseModel):
    telegram_id: int = None
    paid: Optional[bool] = False
    paid_minutes: Optional[int] = Field(ge=0, default=0)
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)