from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.auth.database import get_db
from src.auth.dbmodels import User
from src.auth.dto import UserRegister, UserLogin, UserResponse, TokenResponse
from src.auth.security import hash_password, verify_password, create_access_token

from datetime import datetime, timedelta, timezone
from src.auth.dbmodels import PasswordResetToken
from src.auth.dto import PasswordResetRequest, PasswordResetConfirm
from src.auth.security import generate_reset_token, hash_reset_token
from src.auth.reset_mail import send_password_reset_email


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse)
def register(data: UserRegister, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Email ya registrado")

    user = User(email=data.email, password_hash=hash_password(data.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login(data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()

    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciales inválidas")

    token = create_access_token(user_id=user.id, role=user.role)
    return TokenResponse(access_token=token)


#password reset
@router.post("/password-reset/request")
def request_password_reset(data: PasswordResetRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()

    if user:
        raw_token = generate_reset_token()
        db.add(PasswordResetToken(
            user_id=user.id,
            token_hash=hash_reset_token(raw_token),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
        ))
        db.commit()
        send_password_reset_email(user.email, raw_token)

    return {"message": "Si el email existe, recibirás instrucciones"}


@router.post("/password-reset/confirm")
def confirm_password_reset(data: PasswordResetConfirm, db: Session = Depends(get_db)):
    token_row = db.query(PasswordResetToken).filter(
        PasswordResetToken.token_hash == hash_reset_token(data.token),
        PasswordResetToken.used == False,
    ).first()

    if not token_row or token_row.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Token inválido o expirado")

    user = db.get(User, token_row.user_id)
    user.password_hash = hash_password(data.password)
    token_row.used = True
    db.commit()

    return {"message": "Contraseña actualizada correctamente"}