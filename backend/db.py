from config import POSTGRES_CONFIG
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from typing import AsyncGenerator


DB_URL = f'postgresql+asyncpg://{POSTGRES_CONFIG['USER']}:{POSTGRES_CONFIG['PASSWORD']}@{POSTGRES_CONFIG['HOST']}:{POSTGRES_CONFIG['PORT']}/{POSTGRES_CONFIG['DATABASE']}'

engine = create_async_engine(DB_URL)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session