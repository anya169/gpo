import asyncio
import json
import logging
from typing import Callable, Optional
import bleak
from bleak import BleakClient, BleakScanner
from asyncio_mqtt import Client as MqttClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NeiryHeadbendService:
    def __init__(self):
        self.client: Optional[BleakClient] = None
        self.concentration_callback: Optional[Callable] = None
        self.is_connected = False
        
        self.SERVICE_UUID = "00000000-0000-0000-8000-000000000000"  # Заменить 
        self.CONCENTRATION_CHARACTERISTIC_UUID = "00000000-0000-0000-8000-000000000000"  # Заменить
        
    async def connect(self, device_name: str = "Neiry Headbend") -> bool:
        try:
            logger.info(f"Поиск устройства {device_name}...")
            
            devices = await BleakScanner.discover()
            target_device = None
            
            for device in devices:
                if device_name.lower() in device.name.lower():
                    target_device = device
                    logger.info(f"Найдено устройство: {device.name} - {device.address}")
                    break
            
            if not target_device:
                logger.error(f"Устройство {device_name} не найдено")
                return False
            
            self.client = BleakClient(target_device)
            await self.client.connect()
            self.is_connected = True
            
            logger.info("Успешное подключение к Neiry Headbend")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка подключения: {e}")
            return False
    
    async def start_concentration_stream(self, callback: Callable):
        if not self.client or not self.is_connected:
            raise Exception("Устройство не подключено")
        
        self.concentration_callback = callback
        
        async def notification_handler(sender, data):
            try:
                # Изменить!
                concentration_value = self._parse_concentration_data(data)
                if concentration_value is not None:
                    await self.concentration_callback(concentration_value)
            except Exception as e:
                logger.error(f"Ошибка обработки данных: {e}")
        
        await self.client.start_notify(
            self.CONCENTRATION_CHARACTERISTIC_UUID, 
            notification_handler
        )
        logger.info("Поток концентрации запущен")
    
    def _parse_concentration_data(self, data: bytes) -> Optional[float]:
        #Изменить!
        try:
            if len(data) >= 4:
                value = float(int.from_bytes(data[:4], byteorder='little', signed=False))
                concentration = max(0, min(100, value))
                return concentration
            return None
        except Exception as e:
            logger.error(f"Ошибка парсинга данных: {e}")
            return None
    
    async def disconnect(self):
        if self.client and self.is_connected:
            await self.client.disconnect()
            self.is_connected = False
            logger.info("Отключено от Neiry Headbend")