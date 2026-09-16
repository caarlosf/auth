from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash
import os
from dotenv import load_dotenv
import secrets
import hashlib

#permisos
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from src.auth.database import get_db
from src.auth.dbmodels import User
#fin permisos

load_dotenv()
SECRET_KEY = os.environ["SECRET_KEY"]
ALGORITHM = os.environ["ALGORITHM"]
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"])

password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_hash.verify(plain_password, hashed_password)


def create_access_token(user_id: int) -> str:
    to_encode = {"sub": str(user_id)}
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


#password reset
def generate_reset_token() -> str:
    return secrets.token_urlsafe(32)

def hash_reset_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


#permisos
#averigua que usuario ha hecho la peticion, a partir del token del header Authorization
def get_current_user(
    authorization: str = Header(...),
    db: Session = Depends(get_db),
) -> User:
    credentials_error = HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        "No se pudo validar el token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not authorization.startswith("Bearer "):
        raise credentials_error
    token = authorization.removeprefix("Bearer ")

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_error
    except jwt.PyJWTError:
        raise credentials_error

    user = db.get(User, int(user_id))
    if user is None:
        raise credentials_error
    return user


#comprueba si el usuario actual tiene un permiso concreto
def require_permission(codename: str):
    def checker(user: User = Depends(get_current_user)) -> User:
        user_codenames = {
            permission.codename
            for group in user.groups
            for permission in group.permissions
        }
        if codename not in user_codenames:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "No tienes permiso para hacer esto",
            )
        return user
    return checker

#fin permisos