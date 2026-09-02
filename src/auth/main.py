from fastapi import FastAPI
from src.auth.database import Base, engine
from src.auth import dbmodels
from src.auth.routes import router as auth_router

Base.metadata.create_all(engine)

app = FastAPI()
app.include_router(auth_router)