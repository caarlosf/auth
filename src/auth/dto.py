from pydantic import BaseModel, EmailStr, model_validator #ConfigDict


class PasswordMatch(BaseModel):
    @model_validator(mode="after")
    def passwords_match(self):
        if self.password != self.password2:
            raise ValueError("Las contraseñas no coinciden")
        return self


class UserRegister(PasswordMatch):
    email: EmailStr
    password: str
    password2: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    #model_config = ConfigDict(from_attributes=True)

    #permisos: se quitó el campo role
    id: int
    email: EmailStr
    #fin permisos


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


#password reset
class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(PasswordMatch):
    token: str
    password: str
    password2: str


#permisos
class GroupCreate(BaseModel):
    name: str
    description: str | None = None


class GroupUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class GroupResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
#fin permisos