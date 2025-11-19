from datetime import datetime, timedelta
from fastapi import HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import secrets
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import asyncio
from config import SMTP_CONFIG

from db import get_session
from models import User, AuthCode
from dependencies import create_access_token 

class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def generate_code() -> str:
        """Генерация 6-значного кода"""
        return str(secrets.randbelow(1000000)).zfill(6)

    async def send_code(self, email: str) -> dict:
        email = email.lower().strip()
        
        stmt_user = select(User).where(User.email == email)
        result_user = await self.db.execute(stmt_user)
        existing_user = result_user.scalar_one_or_none()
        
        if existing_user:
            stmt = select(AuthCode).where(
            AuthCode.email == email,
            AuthCode.is_used == False,
            )
            result = await self.db.execute(stmt)

            code = self.generate_code()
            
            auth_code = AuthCode(email=email, code=code)
            self.db.add(auth_code)
            await self.db.commit()

            email_sent = self._send_email(email, code)
            
            if email_sent:
                return {
                    "message": "Код отправлен на вашу почту",
                    "user_exists": existing_user is not None,
                    "user_name": existing_user.name if existing_user else None
                }
            else:
                return {
                    "message": "Код сгенерирован", 
                    "debug_code": code,
                    "user_exists": existing_user is not None,
                    "user_name": existing_user.name if existing_user else None
                }
        else:
            raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Необходима регистрация пользователя"
                )

    def _send_email(self, email_to: str, code: str) -> bool:
        """Отправка email с кодом (синхронный метод)"""
        smtp_host = SMTP_CONFIG["HOST"]
        smtp_port = SMTP_CONFIG["PORT"]
        smtp_user = SMTP_CONFIG["USER"]
        smtp_password = SMTP_CONFIG["PASSWORD"]

        message = MIMEMultipart()
        message["From"] = smtp_user
        message["To"] = email_to
        message["Subject"] = "Код для входа в Concentration App"

        body = f"""
        <h2>Код для входа</h2>
        <p>Ваш код для входа в Concentration App: <strong>{code}</strong></p>
        <p>Код действителен в течение 10 минут.</p>
        <p>Если вы не запрашивали этот код, проигнорируйте это письмо.</p>
        """

        message.attach(MIMEText(body, "html"))

        try:
            with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
                server.login(smtp_user, smtp_password)
                server.sendmail(smtp_user, email_to, message.as_string())
            return True
            
        except Exception as e:
            return False

    async def verify_code(self, email: str, code: str) -> dict:
        """Проверка кода и авторизация/регистрация пользователя"""
        email = email.lower().strip()
        code = code.strip()

        stmt = select(AuthCode).where(
            AuthCode.email == email,
            AuthCode.code == code,
            AuthCode.is_used == False,
        )
        result = await self.db.execute(stmt)
        auth_code = result.scalar_one_or_none()

        if not auth_code:
            stmt_all = select(AuthCode).where(
                AuthCode.email == email
            ).order_by(AuthCode.created_at.desc())
            result_all = await self.db.execute(stmt_all)
            all_codes = result_all.scalars().all()
            
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Неверный или просроченный код"
            )

        auth_code.is_used = True
        await self.db.commit()

        stmt = select(User).where(User.email == email)
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if user:
            access_token = create_access_token(
                data={"user_id": user.user_id, "email": user.email}
            )
            
            return {
                "success": True, 
                "message": "Успешная авторизация",
                "user_id": user.user_id,
                "name": user.name,
                "email": user.email,
                "access_token": access_token,
                "token_type": "bearer",
                "requires_registration": False
            }
        else:
            return {
                "success": True,
                "message": "Пользователь не найден. Требуется регистрация",
                "requires_registration": True,
                "email": email
            }
        
    async def register_user(self, email: str, name: str) -> dict:
        stmt = select(User).where(User.email == email)
        result = await self.db.execute(stmt)
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Пользователь с таким email уже существует"
            )

        user = User(email=email, name=name)
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        
        access_token = create_access_token(
            data={"user_id": user.user_id, "email": user.email}
        )
        
        return {
            "success": True,
            "message": "Пользователь успешно зарегистрирован",
            "user_id": user.user_id,
            "name": user.name,
            "email": user.email,
            "access_token": access_token,
            "token_type": "bearer",
            "requires_registration": False
        }