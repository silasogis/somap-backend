from pydantic import BaseModel, ConfigDict
from humps import camelize
from app.schemas.user import UserResponse

class LoginRequest(BaseModel):
    email: str
    password: str

class LoginResponse(BaseModel):
    model_config = ConfigDict(
        alias_generator=camelize,
        populate_by_name=True,
        from_attributes=True,
    )
    token: str
    user: UserResponse
