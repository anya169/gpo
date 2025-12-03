from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from datetime import datetime
import json
import asyncio

from services.file_data_service import file_data_service
from websocket_manager import manager

router = APIRouter()

@router.websocket("/ws/neiry/file-stream")
async def websocket_file_stream(websocket: WebSocket):
    """WebSocket для передачи данных из файла"""
    
    await websocket.accept()
    print("WebSocket connected")
    
    # Состояние потока
    is_streaming = False
    stream_task = None
    
    try:
        await websocket.send_json({
            "type": "connection_established",
            "message": "Connected to file stream",
            "timestamp": datetime.now().isoformat()
        })
        
        # Основной цикл обработки сообщений
        while True:
            try:
                # Получаем сообщение (блокирующий вызов)
                data = await websocket.receive_text()
                
                # Обрабатываем сообщение
                message = json.loads(data)
                message_type = message.get("type")
                
                if message_type == "start_stream":
                    if not is_streaming:
                        is_streaming = True
                        speed = message.get("speed", 1.0)
                        
                        # Запускаем поток
                        stream_task = asyncio.create_task(send_data_stream(websocket, speed))
                        
                        await websocket.send_json({
                            "type": "stream_started",
                            "speed": speed,
                            "timestamp": datetime.now().isoformat()
                        })
                
                elif message_type == "stop_stream":
                    is_streaming = False
                    if stream_task:
                        stream_task.cancel()
                        stream_task = None
                    
                    await websocket.send_json({
                        "type": "stream_stopped",
                        "timestamp": datetime.now().isoformat()
                    })
                
                elif message_type == "ping":
                    await websocket.send_json({
                        "type": "pong",
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
        print("WebSocket connection closed")

async def send_data_stream(websocket: WebSocket, speed: float):
    """Отправляет поток данных"""
    try:
        index = 0
        data_points = file_data_service.data_points
        
        while True:
            if index >= len(data_points):
                index = 0
            
            data_point = data_points[index]
            
            await websocket.send_json({
                "type": "concentration_data",
                "data": data_point,
                "index": index,
                "total": len(data_points),
                "timestamp": datetime.now().isoformat()
            })
            
            index += 1
            await asyncio.sleep(speed)
            
    except asyncio.CancelledError:
        print("Data stream cancelled")
    except Exception as e:
        print(f"Error in data stream: {e}")

# WebSocket для сессий (из concentration_routers.py)
@router.websocket("/ws/session/{session_id}")
async def websocket_session(websocket: WebSocket, session_id: int):
    """WebSocket для сессий (из вашего concentration_routers.py)"""
    await manager.connect(websocket, session_id)
    
    try:
        await manager.broadcast_to_session(session_id, {
            "type": "connection_established",
            "session_id": session_id,
            "message": "WebSocket подключен"
        })
        
        while True:
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                
                # Пересылаем сообщение через менеджер
                await manager.broadcast_to_session(session_id, {
                    **message,
                    "session_id": session_id,
                    "timestamp": datetime.now().isoformat()
                })
                
            except json.JSONDecodeError:
                await manager.broadcast_to_session(session_id, {
                    "type": "error",
                    "message": "Неверный формат JSON",
                    "timestamp": datetime.now().isoformat()
                })
                
    except WebSocketDisconnect:
        manager.disconnect(session_id)
        print(f"WebSocket отключен для сессии {session_id}")