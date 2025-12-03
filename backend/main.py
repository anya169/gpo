import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware import Middleware

from routers import auth_routers, concentration_routers, neiry_routers
from routers.websocket_routers import router as websocket_router  # Импортируем WebSocket роутер

# Создаем middleware для CORS
middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
]

# Создаем приложение с middleware
app = FastAPI(middleware=middleware, title="Concentration Meter API")

# Подключаем роутеры
app.include_router(auth_routers.router, prefix="/auth", tags=["auth"])
app.include_router(concentration_routers.router, prefix="/api/v1", tags=["concentration"])
app.include_router(neiry_routers.router, prefix="/api/v1", tags=["neiry"])

# ВАЖНО: WebSocket роутер должен быть подключен БЕЗ префикса
app.include_router(websocket_router)

@app.get("/")
async def root():
    return {"message": "Concentration Meter API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "concentration-meter"}

# Тестовый endpoint для проверки WebSocket
@app.get("/test/websocket-urls")
async def get_websocket_urls():
    return {
        "test_websocket": "ws://localhost:8000/ws/neiry/test",
        "file_stream_websocket": "ws://localhost:8000/ws/neiry/file-stream",
        "session_websocket": "ws://localhost:8000/ws/session/{session_id}",
        "instructions": "Use these URLs in your frontend WebSocket connection"
    }

if __name__ == "__main__":
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        ws_ping_interval=20,
        ws_ping_timeout=20,
        timeout_keep_alive=30
    )