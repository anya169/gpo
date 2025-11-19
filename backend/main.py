import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import auth_routers, concentration_routers, neiry_routers

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_routers.router)
app.include_router(concentration_routers.router, prefix="/api/v1")
app.include_router(neiry_routers.router, prefix="/api/v1")

@app.get("/api/v1/neiry/devices")
async def get_available_devices():
    """Получение списка доступных устройств"""
    return {
        "devices": [
            {"type": "Band", "name": "Neiry Band"},
            {"type": "BrainBit", "name": "BrainBit"},
            {"type": "Noise", "name": "Demo Mode"}
        ]
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)