from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.app.db.database import get_db
from backend.app.db.models import User
from backend.app.services.auth_service import decode_token

_bearer = HTTPBearer(auto_error=True)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db=Depends(get_db),
) -> User:
    payload = decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user = db.query(User).filter(User.id == payload["sub"], User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def require_commander(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in ("commander", "analyst"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Commander or analyst role required")
    return current_user
