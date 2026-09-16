from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.auth.database import get_db
from src.auth.dbmodels import User, Group, Permission
from src.auth.dto import (
    UserRegister, UserLogin, UserResponse, TokenResponse,
    GroupCreate, GroupUpdate, GroupResponse, GroupDetailResponse,
    PermissionCreate, PermissionResponse,
)
from src.auth.security import (
    hash_password, verify_password, create_access_token,
    get_current_user, require_permission,
)

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

    is_first_user = db.query(User).count() == 0

    user = User(email=data.email, password_hash=hash_password(data.password))
    db.add(user)
    db.commit()
    db.refresh(user)

    if is_first_user:
        admin_group = db.query(Group).filter(Group.name == "admin").first()
        if admin_group:
            user.groups.append(admin_group)
            db.commit()

    return user


@router.post("/login", response_model=TokenResponse)
def login(data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()

    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciales inválidas")

    token = create_access_token(user_id=user.id)
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

#inicio permisos
#grupos
groups_router = APIRouter(prefix="/groups", tags=["groups"])


@groups_router.post(
    "", response_model=GroupResponse,
    #comprueba el token del usuario y si tiene el permiso, permite ejecutar la funcion, sino devuelve 403 de require_permission en security.py
    dependencies=[Depends(require_permission("groups:create"))],
)
def create_group(data: GroupCreate, db: Session = Depends(get_db)):
    if db.query(Group).filter(Group.name == data.name).first():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Ya existe un grupo con ese nombre")
    group = Group(name=data.name, description=data.description)
    db.add(group)
    db.commit()
    db.refresh(group)
    return group


@groups_router.get("", response_model=list[GroupResponse])
def list_groups(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(Group).all()


@groups_router.get("/{group_id}", response_model=GroupDetailResponse)
def get_group(group_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    group = db.get(Group, group_id)
    if not group:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Grupo no encontrado")
    return group


@groups_router.patch(
    "/{group_id}", response_model=GroupResponse,
    dependencies=[Depends(require_permission("groups:update"))],
)
def update_group(group_id: int, data: GroupUpdate, db: Session = Depends(get_db)):
    group = db.get(Group, group_id)
    if not group:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Grupo no encontrado")
    group.name = data.name
    group.description = data.description
    db.commit()
    db.refresh(group)
    return group


@groups_router.delete(
    "/{group_id}", status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("groups:delete"))],
)
def delete_group(group_id: int, db: Session = Depends(get_db)):
    group = db.get(Group, group_id)
    if not group:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Grupo no encontrado")
    db.delete(group)
    db.commit()


@groups_router.post(
    "/{group_id}/permissions/{permission_id}", response_model=GroupDetailResponse,
    dependencies=[Depends(require_permission("groups:permissions:add"))],
)
def add_permission_to_group(group_id: int, permission_id: int, db: Session = Depends(get_db)):
    group = db.get(Group, group_id)
    permission = db.get(Permission, permission_id)
    if not group or not permission:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Grupo o permiso no encontrado")
    if permission not in group.permissions:
        group.permissions.append(permission)
        db.commit()
        db.refresh(group)
    return group


@groups_router.delete(
    "/{group_id}/permissions/{permission_id}", response_model=GroupDetailResponse,
    dependencies=[Depends(require_permission("groups:permissions:remove"))],
)
def remove_permission_from_group(group_id: int, permission_id: int, db: Session = Depends(get_db)):
    group = db.get(Group, group_id)
    permission = db.get(Permission, permission_id)
    if not group or not permission:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Grupo o permiso no encontrado")
    if permission in group.permissions:
        group.permissions.remove(permission)
        db.commit()
        db.refresh(group)
    return group


@groups_router.post(
    "/{group_id}/users/{user_id}",
    dependencies=[Depends(require_permission("groups:members:add"))],
)
def add_user_to_group(group_id: int, user_id: int, db: Session = Depends(get_db)):
    group = db.get(Group, group_id)
    target_user = db.get(User, user_id)
    if not group or not target_user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Grupo o usuario no encontrado")
    if group not in target_user.groups:
        target_user.groups.append(group)
        db.commit()
    return {"message": "Usuario añadido al grupo"}


@groups_router.delete(
    "/{group_id}/users/{user_id}",
    dependencies=[Depends(require_permission("groups:members:remove"))],
)
def remove_user_from_group(group_id: int, user_id: int, db: Session = Depends(get_db)):
    group = db.get(Group, group_id)
    target_user = db.get(User, user_id)
    if not group or not target_user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Grupo o usuario no encontrado")
    if group in target_user.groups:
        target_user.groups.remove(group)
        db.commit()
    return {"message": "Usuario quitado del grupo"}


#permisos
permissions_router = APIRouter(prefix="/permissions", tags=["permissions"])


@permissions_router.post(
    "", response_model=PermissionResponse,
    dependencies=[Depends(require_permission("permissions:create"))],
)
def create_permission(data: PermissionCreate, db: Session = Depends(get_db)):
    if db.query(Permission).filter(Permission.codename == data.codename).first():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Ya existe un permiso con ese codename")
    permission = Permission(codename=data.codename, description=data.description)
    db.add(permission)
    db.commit()
    db.refresh(permission)
    return permission


@permissions_router.get("", response_model=list[PermissionResponse])
def list_permissions(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(Permission).all()


@permissions_router.delete(
    "/{permission_id}", status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("permissions:delete"))],
)
def delete_permission(permission_id: int, db: Session = Depends(get_db)):
    permission = db.get(Permission, permission_id)
    if not permission:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Permiso no encontrado")
    db.delete(permission)
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