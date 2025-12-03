from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from datetime import datetime
import json
import asyncio

from services.file_data_service import file_data_service
from websocket_manager import manager

router = APIRouter()

# WebSocket для файловых данных
@router.websocket("/ws/neiry/file-stream")
async def websocket_file_stream(websocket: WebSocket):
    """WebSocket для передачи данных из файла Малахова.xlsx"""
    
    # Проверяем origin (важно для CORS)
    origin = websocket.headers.get("origin", "")
    allowed_origins = ["http://localhost:3000", "http://127.0.0.1:3000", "null"]
    
    if origin not in allowed_origins and origin:
        print(f"Blocked connection from origin: {origin}")
        await websocket.close(code=1008)
        return
    
    await websocket.accept()
    
    try:
        print("File stream WebSocket connected")
        
        await websocket.send_json({
            "type": "connection_established",
            "message": "File stream WebSocket connected",
            "timestamp": datetime.now().isoformat()
        })
        
        is_streaming = False
        stream_speed = 1.0
        
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                message_type = message.get("type")
                
                if message_type == "start_stream":
                    if not is_streaming:
                        is_streaming = True
                        stream_speed = message.get("speed", 1.0)
                        
                        await websocket.send_json({
                            "type": "stream_started",
                            "message": "Data stream started",
                            "speed": stream_speed,
                            "timestamp": datetime.now().isoformat()
                        })
                        
                        # Запускаем поток данных
                        async def stream_data():
                            index = 0
                            while is_streaming:
                                if index >= len(file_data_service.data_points):
                                    index = 0
                                
                                data_point = file_data_service.data_points[index]
                                
                                await websocket.send_json({
                                    "type": "concentration_data",
                                    "data": data_point,
                                    "index": index,
                                    "total": len(file_data_service.data_points),
                                    "timestamp": datetime.now().isoformat()
                                })
                                
                                index += 1
                                await asyncio.sleep(stream_speed)
                        
                        asyncio.create_task(stream_data())
                
                elif message_type == "stop_stream":
                    is_streaming = False
                    await websocket.send_json({
                        "type": "stream_stopped",
                        "message": "Data stream stopped",
                        "timestamp": datetime.now().isoformat()
                    })
                
                elif message_type == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.now().isoformat()
                    })
                
                elif message_type == "get_metrics":
                    metrics = await file_data_service.get_current_metrics()
                    await websocket.send_json({
                        "type": "current_metrics",
                        "data": metrics,
                        "timestamp": datetime.now().isoformat()
                    })
                
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON format",
                    "timestamp": datetime.now().isoformat()
                })
            except Exception as e:
                print(f"Error processing message: {e}")
                
    except WebSocketDisconnect:
        print("File stream WebSocket disconnected")
        is_streaming = False
    except Exception as e:
        print(f"WebSocket error: {e}")
        is_streaming = False

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