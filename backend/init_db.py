import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from models import Base
from db import DB_URL

async def create_tables():
    try:
        engine = create_async_engine(DB_URL, echo=True)
        
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            print("Все таблицы успешно созданы")
            
        await engine.dispose()
        
    except Exception as e:
        print(f" Ошибка при создании таблиц: {e}")
        

async def main():
    await create_tables()

if __name__ == "__main__":
    asyncio.run(main())