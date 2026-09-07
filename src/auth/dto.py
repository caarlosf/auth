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

    id: int
    email: EmailStr
    role: str


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