import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware import Middleware
from fastapi import Request
import logging

# Настройка логгирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Создаем middleware для CORS с более гибкими настройками
middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH", "HEAD"],
        allow_headers=["*"],  # Разрешаем все заголовки
        expose_headers=["*"]
    )
]

# Создаем приложение с middleware
app = FastAPI(
    middleware=middleware,
    title="Concentration Meter API",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Добавим свой middleware для логирования
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Request: {request.method} {request.url}")
    logger.info(f"Headers: {dict(request.headers)}")
    
    response = await call_next(request)
    
    logger.info(f"Response: {response.status_code}")
    return response

# Ручной обработчик OPTIONS для всех маршрутов
@app.options("/{path:path}")
async def options_handler(path: str):
    return {
        "message": "CORS preflight",
        "allowed_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH", "HEAD"],
        "allowed_origins": ["http://localhost:3000", "http://127.0.0.1:3000"]
    }

# Подключаем роутеры
from routers import auth_routers, concentration_routers
from routers.websocket_routers import router as websocket_router

app.include_router(auth_routers.router, prefix="/auth", tags=["auth"])
app.include_router(concentration_routers.router, prefix="/api/v1", tags=["concentration"])
app.include_router(websocket_router)


if __name__ == "__main__":
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        ws_ping_interval=20,
        ws_ping_timeout=20,
        timeout_keep_alive=30,
        log_level="debug"
    )