from pydantic import BaseModel, ConfigDict
from humps import camelize
from app.models.user import UserRole

class UserResponse(BaseModel):
    model_config = ConfigDict(
        alias_generator=camelize,
        populate_by_name=True,
        from_attributes=True,
    )
    id: str
    name: str
    email: str
    role: UserRole
