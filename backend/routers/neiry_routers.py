from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio
import json
from datetime import time

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

class ConnectNeiryRequest(BaseModel):
    device_type: str = "Band"  
    device_serial: str = None  # Опционально: конкретный серийный номер

class DiscoverDevicesRequest(BaseModel):
    device_type: str = "Any"
    timeout: int = 30

class SelectDeviceRequest(BaseModel):
    device_serial: str

@router.post("/neiry/discover")
async def discover_devices(
    request: DiscoverDevicesRequest,
    db: AsyncSession = Depends(get_session)
):
    """Поиск всех доступных устройств"""
    try:
        if not neiry_service.capsule_available:
            return {
                "success": False,
                "message": "Capsule API недоступен",
                "devices": []
            }
        
        # Получаем сервис Capsule
        capsule_service = neiry_service.capsule_service
        if not capsule_service:
            return {
                "success": False,
                "message": "Capsule сервис не инициализирован",
                "devices": []
            }
        
        # Инициализируем если нужно
        if not capsule_service.capsule_lib:
            initialized = await capsule_service.initialize()
            if not initialized:
                return {
                    "success": False,
                    "message": "Не удалось инициализировать Capsule",
                    "devices": []
                }
        
        # Ищем устройства
        devices = await capsule_service.discover_devices(
            device_type=request.device_type,
            timeout=request.timeout
        )
        
        return {
            "success": True,
            "message": f"Найдено устройств: {len(devices)}",
            "devices": devices,
            "count": len(devices)
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Ошибка поиска устройств: {str(e)}",
            "devices": []
        }

@router.post("/neiry/select")
async def select_device(
    request: SelectDeviceRequest,
    db: AsyncSession = Depends(get_session)
):
    """Выбор конкретного устройства"""
    try:
        if not neiry_service.capsule_available or not neiry_service.capsule_service:
            return {
                "success": False,
                "message": "Capsule API недоступен"
            }
        
        capsule_service = neiry_service.capsule_service
        
        # Выбираем устройство
        selected = await capsule_service.select_device(request.device_serial)
        
        if not selected:
            return {
                "success": False,
                "message": f"Устройство {request.device_serial} не найдено"
            }
        
        device_info = capsule_service.get_selected_device_info()
        
        return {
            "success": True,
            "message": f"Устройство выбрано: {device_info.get('name', 'Unknown')}",
            "device": device_info
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Ошибка выбора устройства: {str(e)}"
        }

@router.post("/neiry/connect")
async def connect_neiry(
    request: ConnectNeiryRequest,
    db: AsyncSession = Depends(get_session)
):
    """Подключение к нейроинтерфейсу или файловому источнику"""
    
    if request.device_type.lower() == "file":
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
            await manager.broadcast_to_session(1, {
                "type": "concentration_update",
                "data": data
            })
        
        file_data_service.add_concentration_callback(send_to_websocket)
        
        return {
            "connected": success, 
            "device_type": "File", 
            "message": "Файловый источник данных подключен"
        }
    
    else:
        # Подключаем реальное устройство
        try:
            if not neiry_service.capsule_available:
                return {
                    "connected": False,
                    "message": "Capsule API недоступен. Проверьте наличие библиотеки CapsuleClient"
                }
            
            capsule_service = neiry_service.capsule_service
            
            # Если указан серийный номер, выбираем устройство
            if request.device_serial:
                await capsule_service.select_device(request.device_serial)
            
            # Подключаемся к устройству
            success = await neiry_service.connect(request.device_type)
            
            if success:
                # Добавляем колбэк для реального устройства
                async def handle_real_concentration(concentration: float):
                    metrics = await neiry_service.get_current_metrics()
                    
                    data = {
                        "concentration": concentration,
                        "heart_rate": metrics.get("heart_rate", 70),
                        "stress": metrics.get("stress", 50),
                        "focus": metrics.get("focus", 50),
                        "alpha": 0.0,
                        "beta": 0.0,
                        "theta": 0.0,
                        "fatigue_score": 0.0,
                        "relaxation_index": 0.0,
                        "mark": "real_device",
                        "name": metrics.get("selected_device", {}).get("name", "Neiry Device"),
                        "timestamp": time.time(),
                        "device_type": "neiry",
                        "is_calibrated": metrics.get("is_calibrated", False),
                        "is_streaming": metrics.get("is_streaming", False),
                        "device_serial": metrics.get("selected_device", {}).get("serial", "unknown")
                    }
                    
                    await manager.broadcast_to_session(1, {
                        "type": "concentration_update",
                        "data": data
                    })
                
                await neiry_service.start_concentration_stream(handle_real_concentration)
                
                device_info = capsule_service.get_selected_device_info()
                
                return {
                    "connected": success, 
                    "device_type": request.device_type,
                    "message": f"Устройство {device_info.get('name', 'Unknown')} подключено",
                    "device_info": device_info
                }
            else:
                return {
                    "connected": False,
                    "message": "Не удалось подключиться к устройству"
                }
            
        except Exception as e:
            return {
                "connected": False,
                "message": f"Ошибка подключения: {str(e)}"
            }

@router.get("/neiry/devices")
async def get_found_devices():
    """Получение списка найденных устройств"""
    try:
        if not neiry_service.capsule_available or not neiry_service.capsule_service:
            return {
                "success": False,
                "message": "Capsule API недоступен",
                "devices": []
            }
        
        capsule_service = neiry_service.capsule_service
        devices = capsule_service.get_found_devices()
        
        return {
            "success": True,
            "devices": devices,
            "count": len(devices)
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Ошибка: {str(e)}",
            "devices": []
        }

@router.get("/neiry/selected")
async def get_selected_device():
    """Получение информации о выбранном устройстве"""
    try:
        if not neiry_service.capsule_available or not neiry_service.capsule_service:
            return {
                "success": False,
                "message": "Capsule API недоступен",
                "device": None
            }
        
        capsule_service = neiry_service.capsule_service
        device_info = capsule_service.get_selected_device_info()
        
        return {
            "success": True,
            "device": device_info
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Ошибка: {str(e)}",
            "device": None
        }

@router.post("/neiry/calibrate")
async def calibrate_neiry():
    """Калибровка подключенного устройства"""
    try:
        if not neiry_service.capsule_available or not neiry_service.capsule_service:
            return {
                "success": False,
                "message": "Capsule API недоступен"
            }
        
        capsule_service = neiry_service.capsule_service
        
        if not capsule_service.is_connected:
            return {
                "success": False,
                "message": "Устройство не подключено"
            }
        
        # Выполняем калибровку
        calibrated = await capsule_service.calibrate_device()
        
        if calibrated:
            return {
                "success": True,
                "message": "Калибровка завершена успешно"
            }
        else:
            return {
                "success": False,
                "message": "Ошибка калибровки"
            }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Ошибка калибровки: {str(e)}"
        }