from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse


router = APIRouter()


@router.post("/register", response_model=UserResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> UserResponse:
	existing = db.scalar(select(User).where(User.email == payload.email.lower()))
	if existing:
		raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

	user = User(
		name=payload.name.strip(),
		email=payload.email.lower(),
		password_hash=hash_password(payload.password),
		created_at=datetime.now(timezone.utc),
	)
	db.add(user)
	db.commit()
	db.refresh(user)

	return UserResponse(
		id=user.id,
		name=user.name,
		email=user.email,
		created_at=user.created_at,
	)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
	user = db.scalar(select(User).where(User.email == payload.email.lower()))
	if not user or not verify_password(payload.password, user.password_hash):
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

	token = create_access_token(subject=user.email)
	return TokenResponse(access_token=token, token_type="bearer")
