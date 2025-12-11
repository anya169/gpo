from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from datetime import datetime
import json
import asyncio
from typing import Dict

from services.file_data_service import file_data_service
from websocket_manager import manager

router = APIRouter()

async def send_data_stream(websocket: WebSocket, speed: float):
    """Отправляет поток данных в реальном времени"""
    try:
        # Запускаем отслеживание файла
        await file_data_service.start_file_watching()
        
        # Колбэк для отправки данных через WebSocket
        async def send_new_data(concentration: float, data_point: Dict):
            """Колбэк для отправки новых данных"""
            try:
                formatted_data = {
                    "concentration": data_point.get("concentration", 0.0),
                    "focus": data_point.get("focus", 50.0),
                    "stress": data_point.get("stress", 0.0),
                    "heart_rate": data_point.get("heart_rate", 0),
                    "alpha": data_point.get("alpha", 0.0),
                    "beta": data_point.get("beta", 0.0),
                    "theta": data_point.get("theta", 0.0),
                    "data_index": len(file_data_service.data_points) - 1,
                    "total_points": len(file_data_service.data_points),
                    "name": data_point.get("name", "Unknown"),
                    "mark": data_point.get("mark", "None"),
                    "timestamp": data_point.get("timestamp", datetime.now().isoformat()),
                }
                
                await websocket.send_json({
                    "type": "concentration_data",
                    "data": formatted_data,
                    "index": len(file_data_service.data_points) - 1,
                    "total": len(file_data_service.data_points),
                    "timestamp": datetime.now().isoformat()
                })
                
                print(f"Отправлены новые данные: концентрация={concentration}")
                
            except Exception as e:
                print(f"Ошибка отправки данных: {e}")
        
        # Регистрируем колбэк для получения новых данных
        file_data_service.add_concentration_callback(send_new_data)
        
        # Сначала отправляем все существующие данные
        existing_data = file_data_service.get_all_data()
        if existing_data:
            print(f"Отправка {len(existing_data)} существующих записей...")
            for i, data_point in enumerate(existing_data):
                await send_new_data(data_point.get("concentration", 0.0), data_point)
                if i < len(existing_data) - 1:  # Пауза между записями, кроме последней
                    await asyncio.sleep(speed / 2)
        
        print(f"Существующие данные ({len(existing_data)} записей) отправлены. Ожидание новых...")
        
        # Бесконечный цикл для поддержания соединения
        # Новые данные будут отправляться через колбэк
        while True:
            await asyncio.sleep(1)  # Просто ждем
            
    except asyncio.CancelledError:
        print("Data stream cancelled")
    except Exception as e:
        print(f"Error in data stream: {e}")
    finally:
        # Очищаем колбэки при остановке
        file_data_service.concentration_callbacks = []
        await file_data_service.stop_file_watching()

@router.websocket("/ws/neiry/file-stream")
async def websocket_file_stream(websocket: WebSocket):
    await websocket.accept()    
    is_streaming = False
    stream_task = None
    
    try:
        await websocket.send_json({
            "type": "connection_established",
            "message": "Connected to real-time file stream",
            "timestamp": datetime.now().isoformat()
        })
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                message_type = message.get("type")
                
                if message_type == "start_stream":
                    if not is_streaming:
                        is_streaming = True
                        speed = message.get("speed", 1.0)
                        session_id = message.get("session_id", 1)
                        await file_data_service.start_streaming(session_id)
                        stream_task = asyncio.create_task(send_data_stream(websocket, speed))
                        
                        await websocket.send_json({
                            "type": "stream_started",
                            "speed": speed,
                            "session_id": session_id,
                            "timestamp": datetime.now().isoformat(),
                            "mode": "real-time"
                        })
                
                elif message_type == "stop_stream":
                    is_streaming = False
                    if stream_task:
                        stream_task.cancel()
                        stream_task = None
                    
                    await file_data_service.stop_streaming()
                    file_data_service.concentration_callbacks = []
                    
                    await websocket.send_json({
                        "type": "stream_stopped",
                        "timestamp": datetime.now().isoformat()
                    })
                
                elif message_type == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.now().isoformat()
                    })
                
                elif message_type == "get_metrics":
                    # Отправляем текущие метрики
                    metrics = await file_data_service.get_current_metrics()
                    await websocket.send_json({
                        "type": "current_metrics",
                        "data": metrics,
                        "timestamp": datetime.now().isoformat()
                    })
                
                elif message_type == "set_speed":
                    speed = message.get("speed", 1.0)
                    file_data_service.set_stream_speed(speed)
                    
                    await websocket.send_json({
                        "type": "speed_updated",
                        "speed": speed,
                        "timestamp": datetime.now().isoformat()
                    })
                
                elif message_type == "check_new_data":
                    # проверка новых данных
                    await websocket.send_json({
                        "type": "new_data_check",
                        "message": "Checking for new data...",
                        "current_count": len(file_data_service.data_points),
                        "timestamp": datetime.now().isoformat()
                    })
                
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON",
                    "timestamp": datetime.now().isoformat()
                })
    
    except WebSocketDisconnect:
        print("WebSocket disconnected by client")
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        # Всегда очищаем ресурсы
        is_streaming = False
        if stream_task:
            stream_task.cancel()
            try:
                await stream_task
            except asyncio.CancelledError:
                pass
        
        # Останавливаем стриминг
        await file_data_service.stop_streaming()
        
        # Очищаем колбэки
        file_data_service.concentration_callbacks = []
        print("WebSocket connection closed")

@router.websocket("/ws/neiry/realtime")
async def websocket_neiry_realtime(websocket: WebSocket):
    """WebSocket для реального времени с нейроинтерфейса"""
    await websocket.accept()
    
    from services.neiry_service import NeiryHeadbendService
    service = NeiryHeadbendService()
    
    try:
        # Подключаемся к устройству
        connected = await service.connect("Band")
        
        if not connected:
            await websocket.send_json({
                "type": "error",
                "message": "Не удалось подключиться к нейроинтерфейсу"
            })
            return
        
        await websocket.send_json({
            "type": "connection_established",
            "message": "Подключено к нейроинтерфейсу",
            "device_type": "neiry"
        })
        
        # Колбэк для отправки данных через WebSocket
        async def send_concentration_data(concentration: float):
            metrics = await service.get_current_metrics()
            
            await websocket.send_json({
                "type": "concentration_data",
                "data": {
                    "concentration": concentration,
                    **metrics,
                    "timestamp": datetime.now().isoformat()
                }
            })
        
        # Запускаем поток
        await service.start_concentration_stream(send_concentration_data)
        
        # Ждем команды от клиента
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "disconnect":
                break
        
    except WebSocketDisconnect:
        print("WebSocket отключен")
    except Exception as e:
        print(f"Ошибка: {e}")
    finally:
        await service.disconnect()
        await websocket.close()