from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
	name: str = Field(min_length=1, max_length=120)
	email: EmailStr
	password: str = Field(min_length=6, max_length=128)


class LoginRequest(BaseModel):
	email: EmailStr
	password: str = Field(min_length=6, max_length=128)


class UserResponse(BaseModel):
	id: int
	name: str
	email: EmailStr
	created_at: datetime


class TokenResponse(BaseModel):
	access_token: str
	token_type: str = "bearer"
