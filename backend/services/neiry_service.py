import asyncio
from typing import Callable, Optional
from .neiry_capsule_service import NeiryCapsuleService

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

class NeiryHeadbendService:
    def __init__(self):
        self.capsule_service = NeiryCapsuleService()
        self.is_connected = False
        self.concentration_callback = None

    async def connect(self, device_name: str = "Neiry Headbend") -> bool:
        """Подключение к нейроинтерфейсу через Capsule API"""
        try:
            # Инициализируем сервис
            initialized = await self.capsule_service.initialize("./libCapsuleClient.dylib")
            if not initialized:
                return False
            
            # Подключаемся к устройству
            from CapsuleClientPython.DeviceType import DeviceType
            connected = await self.capsule_service.connect_device(DeviceType.Band)
            
            self.is_connected = connected
            return connected
            
        except Exception as e:
            print(f"Ошибка подключения: {e}")
            return False

    async def start_concentration_stream(self, callback: Callable):
        """Запуск потока данных концентрации"""
        self.concentration_callback = callback
        
        if not self.is_connected:
            raise Exception("Устройство не подключено")
        
        # Добавляем колбэк для концентрации
        self.capsule_service.add_concentration_callback(callback)
        
        # Запускаем сессию
        await self.capsule_service.start_session()

    async def get_current_metrics(self) -> dict:
        """Получение текущих метрик"""
        if self.is_connected:
            return self.capsule_service.get_current_metrics()
        return {}

    async def disconnect(self):
        """Отключение от устройства"""
        await self.capsule_service.stop_session()
        self.is_connected = False