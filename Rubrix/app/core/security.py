from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models.user import User
from app.db.session import get_db


pwd_context = CryptContext(
	schemes=["bcrypt_sha256", "bcrypt"],
	deprecated="auto",
)
bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
	return pwd_context.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
	return pwd_context.verify(plain_password, password_hash)


def create_access_token(subject: str) -> str:
	settings = get_settings()
	expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
	payload = {
		"sub": subject,
		"exp": expire,
	}
	return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> str:
	settings = get_settings()
	try:
		payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
	except JWTError as exc:
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail="Invalid or expired token",
		) from exc

	subject = payload.get("sub")
	if not subject:
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
	return str(subject)


def get_current_user(
	credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
	db: Session = Depends(get_db),
) -> User:
	if not credentials or not credentials.credentials:
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")

	email = decode_access_token(credentials.credentials)
	user = db.scalar(select(User).where(User.email == email))
	if not user:
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
	return user
