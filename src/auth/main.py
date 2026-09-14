from fastapi import FastAPI
from src.auth.database import Base, engine, SessionLocal
#from src.auth import dbmodels
from src.auth.dbmodels import Group, Permission
from src.auth.routes import router as auth_router, groups_router, permissions_router

Base.metadata.create_all(engine)

#inicio permisos
#crea el grupo admin y sus permisos si todavia no existen al arrancar la app
#sino abria que entrar la primera vez a la base de datos y crearlo a mano
def primer_admin_group():
    db = SessionLocal()
    try:
        admin_group = db.query(Group).filter(Group.name == "admin").first()
        if not admin_group:
            admin_group = Group(name="admin", description="Administrador")
            db.add(admin_group)

        for codename, description in [
            ("groups:manage", "Crear, editar y borrar grupos. Gestionar los miembros y permisos de los grupos"),
            ("permissions:manage", "Crear y borrar permisos"),
        ]:
            permission = db.query(Permission).filter(Permission.codename == codename).first()
            if not permission:
                permission = Permission(codename=codename, description=description)
                db.add(permission)
            if permission not in admin_group.permissions:
                admin_group.permissions.append(permission)

        db.commit()
    finally:
        db.close()


primer_admin_group()
#fin permisos

app = FastAPI()
app.include_router(auth_router)
#inicio permisos
app.include_router(groups_router)
app.include_router(permissions_router)
#fin permisos