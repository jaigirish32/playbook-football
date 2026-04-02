from uuid import UUID
from pydantic import BaseModel, EmailStr
from app.models.user import RoleEnum


class UserCreate(BaseModel):
    email   : EmailStr
    name    : str
    password: str


class UserOut(BaseModel):
    id    : UUID
    email : str
    name  : str
    role  : RoleEnum

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type  : str
    user        : UserOut