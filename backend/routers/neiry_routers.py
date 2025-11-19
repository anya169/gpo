from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio
import json

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import get_session
from services.neiry_service import NeiryHeadbendService
from services.calibration_service import CalibrationService
from websocket_manager import manager

router = APIRouter()

# Глобальные сервисы
neiry_service = NeiryHeadbendService()
calibration_services = {}

class ConnectNeiryRequest(BaseModel):
    device_type: str = "Band"  # Band, BrainBit, etc.

@router.post("/neiry/connect")
async def connect_neiry(
    request: ConnectNeiryRequest,
    db: AsyncSession = Depends(get_session)
):
    """Подключение к нейроинтерфейсу через Capsule API"""
    success = await neiry_service.connect(request.device_type)
    
    if success:
        # Автоматически запускаем поток данных
        await neiry_service.start_concentration_stream(
            lambda concentration: handle_concentration_data(concentration, db)
        )
    
    return {"connected": success, "device_type": request.device_type}

@router.post("/neiry/disconnect")
async def disconnect_neiry():
    """Отключение от нейроинтерфейса"""
    await neiry_service.disconnect()
    return {"connected": False}

@router.get("/neiry/metrics")
async def get_neiry_metrics():
    """Получение текущих метрик нейроинтерфейса"""
    metrics = await neiry_service.get_current_metrics()
    return metrics

@router.websocket("/ws/neiry/realtime")
async def websocket_neiry_realtime(websocket: WebSocket):
    """WebSocket для реального времени данных нейроинтерфейса"""
    await websocket.accept()
    
    try:
        while True:
            # Отправляем текущие метрики каждую секунду
            metrics = await neiry_service.get_current_metrics()
            await websocket.send_json({
                "type": "neiry_metrics",
                "data": metrics,
                "timestamp": asyncio.get_event_loop().time()
            })
            await asyncio.sleep(1)
            
    except WebSocketDisconnect:
        print("WebSocket отключен")

async def handle_concentration_data(concentration: float, db: AsyncSession):
    """Обработка данных концентрации для интеграции с существующей системой"""
    from services.concentration_service import ConcentrationService
    from services.session_service import SessionService
    
    # Здесь можно добавить логику для определения активной сессии
    # и сохранения данных концентрации в базу
    
    # Пример: отправка через WebSocket
    await manager.broadcast_to_session(1, {  # Нужно определить session_id
        "type": "concentration_update",
        "data": {
            "value": concentration,
            "timestamp": asyncio.get_event_loop().time()
        }
    })