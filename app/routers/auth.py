from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select

from app.core.security import create_access_token, get_current_user, verify_password
from app.db import get_session
from app.models import User
from app.schemas import TokenOut, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenOut, summary="RF-01 · Iniciar sesión (JWT)")
def login(form: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_session)):
    """`username` = email del usuario."""
    user = session.exec(select(User).where(User.email == form.username.lower().strip())).first()
    if not user or not user.activo or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciales incorrectas")
    return TokenOut(access_token=create_access_token(user), rol=user.rol, nombre=user.nombre)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user
