
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserRegister(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    # What the person is: "mentor" is an industry professional
    role: Literal["student", "faculty", "mentor"] = "student"
    major: Optional[str] = Field(default=None, max_length=100)  # students
    year: Optional[str] = Field(default=None, max_length=30)  # students
    title: Optional[str] = Field(default=None, max_length=100)  # faculty and industry
    company: Optional[str] = Field(default=None, max_length=100)  # company, or department for faculty

    @field_validator("username", "name", mode="before")
    @classmethod
    def strip_identity(cls, value):
        return value.strip() if isinstance(value, str) else value


class UserLogin(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("username", mode="before")
    @classmethod
    def strip_username(cls, value):
        return value.strip() if isinstance(value, str) else value
