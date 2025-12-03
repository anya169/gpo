from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_session
from services.auth import AuthService

router = APIRouter()

class SendCodeRequest(BaseModel):
    email: str

class VerifyCodeRequest(BaseModel):
    email: str
    code: str

class RegisterRequest(BaseModel):
    email: str
    name: str

class AuthResponse(BaseModel):
    success: bool
    message: str
    user_id: int = None
    name: str = None
    email: str = None
    access_token: str = None
    token_type: str = None
    requires_registration: bool = False

@router.post("/auth/send-code/", response_model=AuthResponse)
async def send_code(
    request: SendCodeRequest,
    db: AsyncSession = Depends(get_session)
):
    auth_service = AuthService(db)
    result = await auth_service.send_code(request.email)
    return AuthResponse(success=True, message=result["message"])

@router.post("/auth/verify-code/", response_model=AuthResponse)
async def verify_code(
    request: VerifyCodeRequest,
    db: AsyncSession = Depends(get_session)
):
    auth_service = AuthService(db)
    result = await auth_service.verify_code(request.email, request.code)
    return AuthResponse(**result)

@router.post("/auth/register/", response_model=AuthResponse)
async def register_user(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_session)
):
    auth_service = AuthService(db)
    result = await auth_service.register_user(request.email, request.name)
    return AuthResponse(**result)