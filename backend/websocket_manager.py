from fastapi import WebSocket
from typing import Dict, List
import json
import asyncio

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, WebSocket] = {}

        self.message_history: Dict[int, List[Dict]] = {}

    async def connect(self, websocket: WebSocket, session_id: int):
        await websocket.accept()
        self.active_connections[session_id] = websocket
        self.message_history[session_id] = []
        print(f"Клиент подключен к сессии {session_id}")

    def disconnect(self, session_id: int):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            if session_id in self.message_history:
                del self.message_history[session_id]
            print(f"Клиент отключен от сессии {session_id}")

    async def send_concentration_data(self, session_id: int, data: dict):
        if session_id in self.active_connections:
            try:
                message = {
                    "type": "concentration_update",
                    "data": data,
                    "timestamp": asyncio.get_event_loop().time()
                }
                await self.active_connections[session_id].send_json(message)

                self.message_history[session_id].append(message)
                
            except Exception as e:
                print(f"Ошибка отправки данных концентрации: {e}")
                self.disconnect(session_id)

    async def send_exercise_notification(self, session_id: int, exercise_data: dict):
        if session_id in self.active_connections:
            try:
                message = {
                    "type": "exercise_notification", 
                    "data": exercise_data,
                    "timestamp": asyncio.get_event_loop().time()
                }
                await self.active_connections[session_id].send_json(message)
                
                self.message_history[session_id].append(message)
                
            except Exception as e:
                print(f"Ошибка отправки уведомления: {e}")
                self.disconnect(session_id)

    async def send_calibration_progress(self, session_id: int, progress_data: dict):
        if session_id in self.active_connections:
            try:
                message = {
                    "type": "calibration_progress",
                    "data": progress_data,
                    "timestamp": asyncio.get_event_loop().time()
                }
                await self.active_connections[session_id].send_json(message)
                
                self.message_history[session_id].append(message)
                
            except Exception as e:
                print(f"Ошибка отправки прогресса калибровки: {e}")
                self.disconnect(session_id)

    async def broadcast_to_session(self, session_id: int, message: dict):
        if session_id in self.active_connections:
            try:
                if "timestamp" not in message:
                    message["timestamp"] = asyncio.get_event_loop().time()
                    
                await self.active_connections[session_id].send_json(message)
                
                self.message_history[session_id].append(message)
                
            except Exception as e:
                print(f"Ошибка широковещательной отправки: {e}")
                self.disconnect(session_id)

    def get_connected_sessions(self) -> List[int]:
        return list(self.active_connections.keys())

    def is_connected(self, session_id: int) -> bool:
        return session_id in self.active_connections

manager = ConnectionManager()