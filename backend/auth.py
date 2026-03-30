import os
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import bcrypt
from jose import JWTError, jwt

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 8

APP_USER = os.getenv("APP_USER", "nestor")
APP_PASSWORD = os.getenv("APP_PASSWORD", "complemento360")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# Hash once at startup
_hashed_password = bcrypt.hashpw(APP_PASSWORD.encode(), bcrypt.gensalt())


def verify_password(plain: str) -> bool:
    return bcrypt.checkpw(plain.encode(), _hashed_password)


def create_token(username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS)
    return jwt.encode({"sub": username, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token inválido o expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if not username:
            raise credentials_exc
        return username
    except JWTError:
        raise credentials_exc
