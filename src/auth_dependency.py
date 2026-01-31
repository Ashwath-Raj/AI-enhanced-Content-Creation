from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from src.auth import decode_access_token

oauth2_scheme = HTTPBearer()


def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload
