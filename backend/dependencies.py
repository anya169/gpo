from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional

SECRET_KEY = "Kj3FyOqYIqKez25e7JS2nnmVIb5MwM9ykDF30YHf7QKiUJwvgo16b69p8bgX9o5sqa5hdbdspLKwTEmTYeEzHK75WuWsBSWqSKNP6hz11Pgn2dxDdSRjjvXqsForGVXVvkjDCSCqJv9ywVOdEfvvlYOprnLv0uxpa3Dp2EgxO2VOh8n0vh3Ms3qR7O7JqJugTviB6HWKI4jxQSyfu44CxuOmFv5OSkJ1NHmBLsInTIArPLuxoHIPfUPwnYsYkPJd8B6IkxkTik9gykPlFDnpkJ0Oatkg7ubpMsQNZWpyc4wZErXMHF2QoXbJfBxKhBhlAaSh3NaW0JrJU8afSWQjX9Ey3pn3B99t"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 дней

security = HTTPBearer()

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Невалидный токен",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("user_id")
        email: str = payload.get("email")
        if user_id is None or email is None:
            raise credentials_exception
        return {"user_id": user_id, "email": email}
    except JWTError:
        raise credentials_exception