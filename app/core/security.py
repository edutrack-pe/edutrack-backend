from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session

from app.core.config import get_settings
from app.db import get_session
from app.models import Rol, User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def create_access_token(user: User) -> str:
    s = get_settings()
    payload = {
        "sub": str(user.id),
        "rol": user.rol.value,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=s.jwt_expires_minutes),
    }
    return jwt.encode(payload, s.jwt_secret, algorithm=s.jwt_algorithm)


def get_current_user(
    token: str = Depends(oauth2_scheme), session: Session = Depends(get_session)
) -> User:
    s = get_settings()
    no_autorizado = HTTPException(
        status.HTTP_401_UNAUTHORIZED, "Token inválido o expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, s.jwt_secret, algorithms=[s.jwt_algorithm])
        user = session.get(User, int(payload["sub"]))
    except (jwt.PyJWTError, KeyError, ValueError):
        raise no_autorizado
    if not user or not user.activo:
        raise no_autorizado
    return user


def require_role(*roles: Rol):
    """Dependencia RBAC: solo permite el acceso a los roles indicados."""

    def verificador(user: User = Depends(get_current_user)) -> User:
        if user.rol not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "No tienes permiso para esta acción")
        return user

    return verificador
