import asyncio
import time
from typing import Callable, Optional, Dict, Any
import numpy as np
from CapsuleClientPython.Capsule import Capsule
from CapsuleClientPython.DeviceLocator import DeviceLocator
from CapsuleClientPython.DeviceType import DeviceType
from CapsuleClientPython.Device import Device, Device_Connection_Status
from CapsuleClientPython.Emotions import Emotions, Emotions_States
from CapsuleClientPython.Cardio import Cardio, Cardio_Data
from CapsuleClientPython.PhysiologicalStates import PhysiologicalStates, PhysiologicalStates_Value
from CapsuleClientPython.Productivity import Productivity, Productivity_Metrics
from CapsuleClientPython.Calibrator import Calibrator
from CapsuleClientPython.Error import CapsuleException

class NeiryCapsuleService:
    def __init__(self):
        self.capsule_lib = None
        self.device_locator = None
        self.device = None
        self.emotions = None
        self.cardio = None
        self.physiological_states = None
        self.productivity = None
        self.calibrator = None
        
        self.is_connected = False
        self.is_calibrated = False
        self.concentration_callbacks = []
        self.heart_rate_callbacks = []
        self.stress_callbacks = []
        
        # Данные в реальном времени
        self.current_concentration = 0.0
        self.current_heart_rate = 0.0
        self.current_stress = 0.0
        self.focus_level = 0.0

    async def initialize(self, library_path: str = "./libCapsuleClient.dylib"):
        """Инициализация библиотеки Capsule"""
        try:
            self.capsule_lib = Capsule(library_path)
            print(f"Capsule version: {self.capsule_lib.get_version()}")
            
            self.device_locator = DeviceLocator('Logs', self.capsule_lib.get_lib())
            self.device_locator.set_on_devices_list(self._on_device_list)
            
            return True
        except Exception as e:
            print(f"Ошибка инициализации Capsule: {e}")
            return False

    async def connect_device(self, device_type: DeviceType = DeviceType.Band, timeout: int = 30):
        """Поиск и подключение к устройству"""
        try:
            # Запускаем поиск устройств
            self.device_locator.request_devices(device_type, timeout)
            
            # Ждем обнаружения устройства
            device_found = await self._wait_for_device(timeout)
            if not device_found or not self.device:
                raise Exception("Устройство не найдено")
            
            # Настраиваем колбэки
            self.device.set_on_connection_status_changed(self._on_connection_status_changed)
            
            # Подключаемся
            self.device.connect(bipolarChannels=True)
            
            # Ждем подключения
            connected = await self._wait_for_connection(timeout)
            if not connected:
                raise Exception("Не удалось подключиться к устройству")
            
            # Инициализируем классификаторы
            await self._initialize_classifiers()
            
            self.is_connected = True
            return True
            
        except Exception as e:
            print(f"Ошибка подключения: {e}")
            return False

    async def start_session(self):
        """Начало сессии сбора данных"""
        if not self.is_connected or not self.device:
            raise Exception("Устройство не подключено")
        
        try:
            self.device.start()
            print("Сессия начата")
            
            # Запускаем калибровку
            await self._calibrate()
            
            return True
            
        except Exception as e:
            print(f"Ошибка начала сессии: {e}")
            return False

    async def stop_session(self):
        """Остановка сессии"""
        try:
            if self.device:
                self.device.stop()
                self.device.disconnect()
                self.is_connected = False
                self.is_calibrated = False
                print("Сессия остановлена")
        except Exception as e:
            print(f"Ошибка остановки сессии: {e}")

    def add_concentration_callback(self, callback: Callable[[float], None]):
        """Добавление колбэка для данных концентрации"""
        self.concentration_callbacks.append(callback)

    def add_heart_rate_callback(self, callback: Callable[[float], None]):
        """Добавление колбэка для данных пульса"""
        self.heart_rate_callbacks.append(callback)

    def add_stress_callback(self, callback: Callable[[float], None]):
        """Добавление колбэка для данных стресса"""
        self.stress_callbacks.append(callback)

    def get_current_metrics(self) -> Dict[str, Any]:
        """Получение текущих метрик"""
        return {
            "concentration": self.current_concentration,
            "heart_rate": self.current_heart_rate,
            "stress": self.current_stress,
            "focus": self.focus_level,
            "is_calibrated": self.is_calibrated,
            "is_connected": self.is_connected
        }

    # Приватные методы
    async def _wait_for_device(self, timeout: int) -> bool:
        """Ожидание обнаружения устройства"""
        for _ in range(timeout * 2):
            self.device_locator.update()
            if self.device:
                return True
            await asyncio.sleep(0.5)
        return False

    async def _wait_for_connection(self, timeout: int) -> bool:
        """Ожидание подключения устройства"""
        for _ in range(timeout * 2):
            if self.device and self.device.is_connected():
                return True
            await asyncio.sleep(0.5)
        return False

    async def _initialize_classifiers(self):
        """Инициализация классификаторов"""
        try:
            # Emotions classifier
            self.emotions = Emotions(self.device, self.capsule_lib.get_lib())
            self.emotions.set_on_states_update(self._on_emotions_states)
            
            # Cardio classifier
            self.cardio = Cardio(self.device, self.capsule_lib.get_lib())
            self.cardio.set_on_indexes_update(self._on_cardio_indexes)
            
            # Physiological States
            self.physiological_states = PhysiologicalStates(self.device, self.capsule_lib.get_lib())
            self.physiological_states.set_on_states(self._on_physiological_states)
            
            # Productivity
            self.productivity = Productivity(self.device, self.capsule_lib.get_lib())
            self.productivity.set_on_metrics_update(self._on_productivity_metrics)
            
            # Calibrator
            self.calibrator = Calibrator(self.device, self.capsule_lib.get_lib())
            
            print("Классификаторы инициализированы")
            
        except Exception as e:
            print(f"Ошибка инициализации классификаторов: {e}")

    async def _calibrate(self):
        """Калибровка устройства"""
        try:
            if self.calibrator:
                # Быстрая калибровка с закрытыми глазами
                self.calibrator.calibrate_quick()
                
                # Ждем завершения калибровки
                await asyncio.sleep(35)  # Быстрая калибровка занимает ~30 секунд
                
                if self.calibrator.is_calibrated():
                    self.is_calibrated = True
                    print("Калибровка завершена успешно")
                else:
                    print("Калибровка не завершена")
                    
        except Exception as e:
            print(f"Ошибка калибровки: {e}")

    # Колбэки данных
    def _on_device_list(self, locator, info, fail_reason):
        """Колбэк списка устройств"""
        if info and len(info) > 0:
            device_info = info[0]
            print(f"Найдено устройство: {device_info.get_name()} ({device_info.get_serial()})")
            self.device = Device(locator, device_info.get_serial(), locator.get_lib())

    def _on_connection_status_changed(self, device, status):
        """Колбэк изменения статуса подключения"""
        print(f"Статус подключения: {status}")

    def _on_emotions_states(self, emotion, emotion_states: Emotions_States):
        """Колбэк эмоциональных состояний"""
        try:
            # Обновляем концентрацию (фокус)
            self.focus_level = emotion_states.focus
            self.current_concentration = emotion_states.focus
            
            # Вызываем колбэки концентрации
            for callback in self.concentration_callbacks:
                callback(emotion_states.focus)
                
        except Exception as e:
            print(f"Ошибка обработки эмоций: {e}")

    def _on_cardio_indexes(self, cardio, indexes: Cardio_Data):
        """Колбэк кардиоданных"""
        try:
            if indexes.metricsAvailable:
                self.current_heart_rate = indexes.heartRate
                self.current_stress = indexes.stressIndex
                
                # Вызываем колбэки
                for callback in self.heart_rate_callbacks:
                    callback(indexes.heartRate)
                    
                for callback in self.stress_callbacks:
                    callback(indexes.stressIndex)
                    
        except Exception as e:
            print(f"Ошибка обработки кардиоданных: {e}")

    def _on_physiological_states(self, phy, states: PhysiologicalStates_Value):
        """Колбэк физиологических состояний"""
        try:
            # Можно использовать для дополнительной аналитики
            pass
        except Exception as e:
            print(f"Ошибка обработки физиологических состояний: {e}")

    def _on_productivity_metrics(self, prod, metrics: Productivity_Metrics):
        """Колбэк метрик продуктивности"""
        try:
            # Дополнительные метрики продуктивности
            pass
        except Exception as e:
            print(f"Ошибка обработки метрик продуктивности: {e}")