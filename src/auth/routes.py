from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.auth.database import get_db
from src.auth.dbmodels import User
from src.auth.dto import UserRegister, UserLogin, UserResponse, TokenResponse
#permisos
from src.auth.security import hash_password, verify_password, create_access_token, get_current_user
#fin permisos

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

    #permisos: ya no se pasa role
    token = create_access_token(user_id=user.id)
    #fin permisos
    return TokenResponse(access_token=token)


#permisos
@router.get("/me", response_model=UserResponse)
def read_me(current_user: User = Depends(get_current_user)):
    return current_user
#fin permisos


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



#permisos
from src.auth.dbmodels import Group
from src.auth.dto import GroupCreate, GroupUpdate, GroupResponse
#fin permisos


#permisos
@router.post("/groups", response_model=GroupResponse, status_code=status.HTTP_201_CREATED)
def create_group(data: GroupCreate, db: Session = Depends(get_db)):
    if db.query(Group).filter(Group.name == data.name).first():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Ya existe un grupo con ese nombre")

    group = Group(name=data.name, description=data.description)
    db.add(group)
    db.commit()
    db.refresh(group)
    return group


@router.get("/groups", response_model=list[GroupResponse])
def list_groups(db: Session = Depends(get_db)):
    return db.query(Group).all()


@router.get("/groups/{group_id}", response_model=GroupResponse)
def get_group(group_id: int, db: Session = Depends(get_db)):
    group = db.get(Group, group_id)
    if not group:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Grupo no encontrado")
    return group


@router.put("/groups/{group_id}", response_model=GroupResponse)
def update_group(group_id: int, data: GroupUpdate, db: Session = Depends(get_db)):
    group = db.get(Group, group_id)
    if not group:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Grupo no encontrado")

    if data.name is not None:
        group.name = data.name
    if data.description is not None:
        group.description = data.description

    db.commit()
    db.refresh(group)
    return group


@router.delete("/groups/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_group(group_id: int, db: Session = Depends(get_db)):
    group = db.get(Group, group_id)
    if not group:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Grupo no encontrado")

    db.delete(group)
    db.commit()
#fin permisos






#html basico para que funcione el enlace de mail de recuperacion de contraseña mientras no creo frontend
#hace falta POST para el token al cambiar la contraseña. El enlace del email necesita GET 
@router.get("/password-reset/confirm", response_class=HTMLResponse)
def reset_password_form(token: str):
    return f"""
    <html>
      <head>
        <style>
          body {{
            background-color: #121212;
            color: #e0e0e0;
            font-family: sans-serif;
            display: flex;
            flex-direction: column;
            align-items: center;
            padding-top: 60px;
          }}
          h2 {{
            color: #ffffff;
          }}
          input {{
            background-color: #1e1e1e;
            color: #e0e0e0;
            border: 1px solid #333;
            border-radius: 4px;
            padding: 8px;
            margin: 6px 0;
            width: 220px;
          }}
          input::placeholder {{
            color: #888;
          }}
          button {{
            background-color: #333;
            color: #e0e0e0;
            border: 1px solid #555;
            border-radius: 4px;
            padding: 8px 16px;
            margin-top: 10px;
            cursor: pointer;
          }}
          button:hover {{
            background-color: #444;
          }}
          #result {{
            color: #f0f0f0;
          }}
        </style>
      </head>
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