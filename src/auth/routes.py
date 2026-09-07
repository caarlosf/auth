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
from src.auth.reset_mail_pass import send_password_reset_email

#html basico para que funcione el enlace de mail de recuperacion de contraseña mientras no creo frontend
from fastapi.responses import HTMLResponse


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
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Token inválido u expirado")

    user = db.get(User, token_row.user_id)
    user.password_hash = hash_password(data.password)
    token_row.used = True
    db.commit()

    return {"message": "Contraseña actualizada correctamente"}




#html basico para que funcione el enlace de mail de recuperacion de contraseña mientras no creo frontend
#hace falta POST para el token al cambiar la contraseña. El enlace del email necesita GET 
@router.get("/password-reset/confirm", response_class=HTMLResponse)
def reset_password_form(token: str):
    return f"""
    <html>
      <body>
        <h2>Restablecer contraseña</h2>
        <form id="resetForm">
          <input type="password" id="password" placeholder="Nueva contraseña"><br>
          <input type="password" id="password2" placeholder="Repite la contraseña"><br>
          <button type="submit">Cambiar contraseña</button>
        </form>
        <p id="result"></p>

        <script>
          document.getElementById("resetForm").addEventListener("submit", async (e) => {{
            e.preventDefault();
            const res = await fetch("/auth/password-reset/confirm", {{
              method: "POST",
              headers: {{ "Content-Type": "application/json" }},
              body: JSON.stringify({{
                token: "{token}",
                password: document.getElementById("password").value,
                password2: document.getElementById("password2").value
              }})
            }});
            const data = await res.json();
            document.getElementById("result").innerText = data.message || data.detail || "Error inesperado";
          }});
        </script>
      </body>
    </html>
    """