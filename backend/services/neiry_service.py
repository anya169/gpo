import asyncio
from typing import Callable, Optional
import sys
import os

# Добавляем путь для импорта
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from .neiry_capsule_service import NeiryCapsuleService
from .file_data_service import file_data_service

class NeiryHeadbendService:
    def __init__(self):
        self.capsule_service = None
        self.is_connected = False
        self.device_type = "file"  # По умолчанию файловый источник
        self.concentration_callback = None
        
        # Попытка инициализировать Capsule сервис
        try:
            self.capsule_service = NeiryCapsuleService()
            self.capsule_available = True
        except ImportError:
            self.capsule_available = False
            print("CapsuleClientPython недоступен, используется только файловый режим")

    async def connect(self, device_type: str = "Band") -> bool:
        """Подключение к устройству или файловому источнику"""
        self.device_type = device_type
        
        if device_type.lower() == "file":
            # Используем файловый источник
            self.is_connected = True
            return True
        
        elif self.capsule_available and self.capsule_service:
            # Подключаемся к реальному устройству через Capsule
            try:
                # Инициализируем библиотеку
                initialized = await self.capsule_service.initialize()
                if not initialized:
                    return False
                
                # Подключаемся к устройству
                connected = await self.capsule_service.connect_device(device_type)
                if not connected:
                    return False
                
                # Калибруем устройство
                calibrated = await self.capsule_service.calibrate_device()
                if not calibrated:
                    print("Калибровка не удалась, но продолжаем работу")
                
                self.is_connected = True
                return True
                
            except Exception as e:
                print(f"Ошибка подключения к нейроинтерфейсу: {e}")
                return False
        
        else:
            print(f"Тип устройства {device_type} не поддерживается или Capsule недоступен")
            return False

    async def start_concentration_stream(self, callback: Callable):
        """Запуск потока данных концентрации"""
        self.concentration_callback = callback
        
        if self.device_type.lower() == "file":
            # Файловый режим
            def file_callback(concentration: float, metrics: dict):
                callback(concentration)
            
            file_data_service.add_concentration_callback(file_callback)
            
        elif self.capsule_available and self.capsule_service and self.is_connected:
            # Режим реального устройства
            self.capsule_service.add_concentration_callback(callback)
            await self.capsule_service.start_streaming()
        
        else:
            raise Exception("Не удалось запустить поток данных")

    async def get_current_metrics(self) -> dict:
        """Получение текущих метрик"""
        if self.device_type.lower() == "file":
            return await file_data_service.get_current_metrics()
        
        elif self.capsule_available and self.capsule_service:
            metrics = self.capsule_service.get_current_metrics()
            metrics["device_type"] = "neiry"
            return metrics
        
        return {}

    async def disconnect(self):
        """Отключение"""
        if self.device_type.lower() == "file":
            await file_data_service.stop_streaming()
        
        elif self.capsule_available and self.capsule_service:
            await self.capsule_service.disconnect()
        
        self.is_connected = False