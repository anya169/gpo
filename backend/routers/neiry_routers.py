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
from services.file_data_service import file_data_service 
from services.calibration_service import CalibrationService
from websocket_manager import manager
from dependencies import get_current_user

router = APIRouter()

# Глобальные сервисы
neiry_service = NeiryHeadbendService()
calibration_services = {}

class ConnectNeiryRequest(BaseModel):
    device_type: str = "Band"  

@router.post("/neiry/connect")
async def connect_neiry(
    request: ConnectNeiryRequest,
    db: AsyncSession = Depends(get_session)
):
    """Подключение к нейроинтерфейсу или файловому источнику"""
    
    if request.device_type == "File":
        # Используем файловый источник данных
        success = True
        
        # Добавляем колбэк для отправки данных через WebSocket
        async def send_to_websocket(concentration: float, metrics: dict):
            data = {
                "concentration": concentration,
                "heart_rate": metrics["heart_rate"],
                "stress": metrics["stress"],
                "focus": metrics["focus"],
                "alpha": metrics["alpha"],
                "beta": metrics["beta"],
                "theta": metrics["theta"],
                "fatigue_score": metrics["fatigue_score"],
                "relaxation_index": metrics["relaxation_index"],
                "mark": metrics["mark"],
                "name": metrics["name"],
                "timestamp": metrics["timestamp"],
                "data_index": metrics["data_index"],
                "total_points": metrics["total_points"],
                "device_type": "file"
            }
            # Отправляем через существующий менеджер
            await manager.broadcast_to_session(1, {  # Используем session_id = 1 по умолчанию
                "type": "concentration_update",
                "data": data
            })
        
        file_data_service.add_concentration_callback(send_to_websocket)
        
        return {"connected": success, "device_type": "File", "message": "Файловый источник данных подключен"}
    
    else:
        # Оригинальная логика для реального устройства
        success = await neiry_service.connect(request.device_type)
        
        if success:
            await neiry_service.start_concentration_stream(
                lambda concentration: handle_concentration_data(concentration, db)
            )
        
        return {"connected": success, "device_type": request.device_type}

@router.post("/neiry/start-file-stream")
async def start_file_stream(
    session_id: int = 1,
    speed: float = 1.0,
    user_data: dict = Depends(get_current_user)
):
    """Запуск потоковой передачи данных из файла"""
    file_data_service.set_stream_speed(speed)
    await file_data_service.start_streaming(session_id)
    
    return {
        "success": True,
        "message": "Потоковая передача данных из файла запущена",
        "session_id": session_id,
        "speed": speed,
        "total_data_points": len(file_data_service.get_all_data())
    }

@router.post("/neiry/stop-file-stream")
async def stop_file_stream(user_data: dict = Depends(get_current_user)):
    """Остановка потоковой передачи данных из файла"""
    await file_data_service.stop_streaming()
    
    return {
        "success": True,
        "message": "Потоковая передача данных остановлена"
    }

@router.get("/neiry/file-metrics")
async def get_file_metrics(user_data: dict = Depends(get_current_user)):
    """Получение текущих метрик из файла"""
    metrics = await file_data_service.get_current_metrics()
    
    return {
        "success": True,
        "metrics": metrics
    }

@router.post("/neiry/set-file-speed")
async def set_file_stream_speed(
    speed: float,
    user_data: dict = Depends(get_current_user)
):
    """Установка скорости потоковой передачи"""
    file_data_service.set_stream_speed(speed)
    
    return {
        "success": True,
        "message": f"Скорость установлена: {speed} секунд между обновлениями",
        "speed": speed
    }

@router.get("/neiry/file-data")
async def get_all_file_data(user_data: dict = Depends(get_current_user)):
    """Получение всех данных из файла"""
    all_data = file_data_service.get_all_data()
    
    return {
        "success": True,
        "total_points": len(all_data),
        "data": all_data
    }

@router.post("/neiry/disconnect")
async def disconnect_neiry():
    """Отключение от нейроинтерфейса или файлового источника"""
    await neiry_service.disconnect()
    await file_data_service.stop_streaming()
    return {"connected": False}

@router.get("/neiry/metrics")
async def get_neiry_metrics():
    """Получение текущих метрик нейроинтерфейса или файла"""
    # Если файловый поток активен, возвращаем файловые метрики
    if file_data_service.is_streaming:
        metrics = await file_data_service.get_current_metrics()
        metrics["device_type"] = "file"
    else:
        metrics = await neiry_service.get_current_metrics()
        metrics["device_type"] = "neiry"
    
    return metrics

@router.websocket("/ws/neiry/realtime")
async def websocket_neiry_realtime(websocket: WebSocket):
    """WebSocket для реального времени данных (работает и с нейроинтерфейсом и с файлом)"""
    await websocket.accept()
    
    try:
        # Отправляем начальное состояние
        initial_metrics = await get_neiry_metrics()
        await websocket.send_json({
            "type": "initial_state",
            "data": {
                "is_streaming": file_data_service.is_streaming or neiry_service.is_connected,
                "current_metrics": initial_metrics
            }
        })
        
        # Ждем сообщений от клиента
        while True:
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                await handle_websocket_message(message, websocket)
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Неверный формат JSON"
                })
                
    except WebSocketDisconnect:
        print("WebSocket отключен")

async def handle_websocket_message(message: dict, websocket: WebSocket):
    """Обработка сообщений от клиента"""
    message_type = message.get("type")
    
    if message_type == "start_file_stream":
        session_id = message.get("session_id", 1)
        speed = message.get("speed", 1.0)
        
        file_data_service.set_stream_speed(speed)
        await file_data_service.start_streaming(session_id)
        
        await websocket.send_json({
            "type": "stream_started",
            "session_id": session_id,
            "speed": speed,
            "device_type": "file"
        })
    
    elif message_type == "stop_file_stream":
        await file_data_service.stop_streaming()
        
        await websocket.send_json({
            "type": "stream_stopped",
            "device_type": "file"
        })
    
    elif message_type == "set_speed":
        speed = message.get("speed", 1.0)
        file_data_service.set_stream_speed(speed)
        
        await websocket.send_json({
            "type": "speed_updated",
            "speed": speed
        })
    
    elif message_type == "get_metrics":
        metrics = await get_neiry_metrics()
        
        await websocket.send_json({
            "type": "current_metrics",
            "metrics": metrics
        })

async def handle_concentration_data(concentration: float, db: AsyncSession):
    """Обработка данных концентрации для интеграции с существующей системой"""
    from services.concentration_service import ConcentrationService
    from services.session_service import SessionService
    
    # Отправка через WebSocket
    await manager.broadcast_to_session(1, {
        "type": "concentration_update",
        "data": {
            "value": concentration,
            "timestamp": asyncio.get_event_loop().time(),
            "device_type": "neiry"
        }
    })