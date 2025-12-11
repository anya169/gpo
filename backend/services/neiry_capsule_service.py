import asyncio
import time
from typing import Callable, Optional, Dict, Any, List
import numpy as np
import os
import sys

# Добавляем путь к CapsuleClientPython
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'CapsuleClientPython'))

try:
    from CapsuleClientPython.Capsule import Capsule
    from CapsuleClientPython.DeviceLocator import DeviceLocator
    from CapsuleClientPython.DeviceType import DeviceType
    from CapsuleClientPython.Device import Device, Device_Connection_Status
    from CapsuleClientPython.DeviceInfo import DeviceInfo
    from CapsuleClientPython.Emotions import Emotions, Emotions_States
    from CapsuleClientPython.Cardio import Cardio, Cardio_Data
    from CapsuleClientPython.Productivity import Productivity, Productivity_Metrics
    from CapsuleClientPython.Calibrator import Calibrator
    from CapsuleClientPython.Error import CapsuleException
    CAPSULE_AVAILABLE = True
except ImportError as e:
    print(f"CapsuleClientPython not available: {e}")
    CAPSULE_AVAILABLE = False

class NeiryDevice:
    """Класс для представления найденного устройства"""
    def __init__(self, info: DeviceInfo, locator: DeviceLocator):
        self.serial = info.get_serial()
        self.name = info.get_name()
        self.type = info.get_type()
        self.info = info
        self.locator = locator
        
    def to_dict(self):
        return {
            "serial": self.serial,
            "name": self.name,
            "type": str(self.type),
            "display_name": f"{self.name} ({self.serial})"
        }

class NeiryCapsuleService:
    def __init__(self):
        if not CAPSULE_AVAILABLE:
            raise ImportError("CapsuleClientPython библиотека не найдена")
        
        self.capsule_lib = None
        self.device_locator = None
        self.device = None
        self.emotions = None
        self.cardio = None
        self.productivity = None
        self.calibrator = None
        
        self.is_connected = False
        self.is_calibrated = False
        self.is_streaming = False
        
        # Список найденных устройств
        self.found_devices: List[NeiryDevice] = []
        self.selected_device: Optional[NeiryDevice] = None
        
        # Колбэки для данных
        self.concentration_callbacks = []
        self.heart_rate_callbacks = []
        self.stress_callbacks = []
        self.focus_callbacks = []
        
        # События
        self.devices_found_event = asyncio.Event()
        self.device_selected_event = asyncio.Event()
        self.device_connected_event = asyncio.Event()
        self.calibration_complete_event = asyncio.Event()
        
        # Текущие данные
        self.current_concentration = 0.0
        self.current_heart_rate = 0.0
        self.current_stress = 0.0
        self.current_focus = 0.0
        
        # Для асинхронности
        self.event_loop = asyncio.get_event_loop()
        self.stop_event = asyncio.Event()

    async def initialize(self, library_path: str = None):
        """Инициализация библиотеки Capsule"""
        try:
            if library_path is None:
                # Пытаемся найти библиотеку
                possible_paths = [
                    "./CapsuleClientPython/libCapsuleClient.dylib",  # macOS
                    "./CapsuleClientPython/CapsuleClient.dll",       # Windows
                    "./libCapsuleClient.dylib",
                    "./CapsuleClient.dll"
                ]
                
                for path in possible_paths:
                    if os.path.exists(path):
                        library_path = path
                        break
                
                if library_path is None:
                    raise FileNotFoundError("Не найдена библиотека CapsuleClient")
            
            self.capsule_lib = Capsule(library_path)
            print(f"Capsule version: {self.capsule_lib.get_version()}")
            
            self.device_locator = DeviceLocator('Logs', self.capsule_lib.get_lib())
            
            return True
            
        except Exception as e:
            print(f"Ошибка инициализации Capsule: {e}")
            return False

    async def discover_devices(self, device_type: str = "Any", timeout: int = 30) -> List[Dict[str, Any]]:
        """
        Поиск всех доступных устройств
        
        Args:
            device_type: Тип устройства ("Any", "Band", "BrainBit", etc.)
            timeout: Таймаут поиска в секундах
            
        Returns:
            Список найденных устройств в формате словарей
        """
        print(f"🔍 Поиск устройств типа: {device_type}")
        
        # Преобразуем строковый тип в DeviceType
        device_type_map = {
            "Any": DeviceType.Any,
            "Band": DeviceType.Band,
            "BrainBit": DeviceType.BrainBit,
            "Headphones": DeviceType.Headphones,
            "Noise": DeviceType.Noise,
            "SinWave": DeviceType.SinWave,
            "Buds": DeviceType.Buds,
            "Impulse": DeviceType.Impulse
        }
        
        capsule_device_type = device_type_map.get(device_type, DeviceType.Any)
        
        # Очищаем список найденных устройств
        self.found_devices = []
        self.devices_found_event.clear()
        
        # Колбэк для получения списка устройств
        def on_device_list(locator, info_list, fail_reason):
            print(f"📡 Получен список устройств: найдено {len(info_list)} устройств")
            
            self.found_devices = []
            for info in info_list:
                device = NeiryDevice(info, locator)
                self.found_devices.append(device)
                print(f"   📱 Найдено: {device.name} ({device.serial}) - {device.type}")
            
            self.event_loop.call_soon_threadsafe(self.devices_found_event.set)
        
        # Настраиваем колбэк
        self.device_locator.set_on_devices_list(on_device_list)
        
        # Запускаем поиск
        self.device_locator.request_devices(capsule_device_type, timeout)
        
        # Ждем завершения поиска
        try:
            await asyncio.wait_for(self.devices_found_event.wait(), timeout=timeout)
            print(f"✅ Поиск завершен. Найдено устройств: {len(self.found_devices)}")
        except asyncio.TimeoutError:
            print("⏱️  Таймаут поиска устройств")
        
        # Обновляем device locator еще раз для получения всех данных
        for _ in range(10):
            self.device_locator.update()
            await asyncio.sleep(0.1)
        
        # Возвращаем список устройств в формате словарей
        return [device.to_dict() for device in self.found_devices]

    async def select_device(self, device_serial: str) -> bool:
        """
        Выбор устройства по серийному номеру
        
        Args:
            device_serial: Серийный номер устройства
            
        Returns:
            True если устройство выбрано успешно
        """
        print(f"🎯 Выбираем устройство: {device_serial}")
        
        # Ищем устройство в списке найденных
        selected = None
        for device in self.found_devices:
            if device.serial == device_serial:
                selected = device
                break
        
        if not selected:
            print(f"❌ Устройство с серийным номером {device_serial} не найдено")
            return False
        
        self.selected_device = selected
        print(f"✅ Выбрано устройство: {selected.name} ({selected.serial})")
        
        # Создаем объект Device
        self.device = Device(
            self.selected_device.locator,
            self.selected_device.serial,
            self.selected_device.locator.get_lib()
        )
        
        self.device_selected_event.set()
        return True

    async def select_device_by_index(self, index: int) -> bool:
        """
        Выбор устройства по индексу в списке
        
        Args:
            index: Индекс устройства в списке (начиная с 0)
            
        Returns:
            True если устройство выбрано успешно
        """
        if index < 0 or index >= len(self.found_devices):
            print(f"❌ Неверный индекс устройства: {index}")
            return False
        
        device = self.found_devices[index]
        return await self.select_device(device.serial)

    def get_found_devices(self) -> List[Dict[str, Any]]:
        """Получение списка найденных устройств"""
        return [device.to_dict() for device in self.found_devices]

    def get_selected_device_info(self) -> Optional[Dict[str, Any]]:
        """Получение информации о выбранном устройстве"""
        if self.selected_device:
            return self.selected_device.to_dict()
        return None

    def _on_connection_status_changed(self, device, status):
        """Колбэк изменения статуса подключения"""
        print(f"Статус подключения: {status}")
        if status == Device_Connection_Status.Connected:
            self.is_connected = True
            self.event_loop.call_soon_threadsafe(self.device_connected_event.set)

    def _on_emotions_states(self, emotion, emotion_states: Emotions_States):
        """Колбэк эмоциональных состояний"""
        try:
            # Обновляем концентрацию (фокус)
            self.current_focus = emotion_states.focus
            self.current_concentration = emotion_states.focus
            self.current_stress = emotion_states.stress
            
            # Вызываем колбэки
            for callback in self.concentration_callbacks:
                callback(emotion_states.focus)
            
            for callback in self.focus_callbacks:
                callback(emotion_states.focus)
                
            for callback in self.stress_callbacks:
                callback(emotion_states.stress)
                
        except Exception as e:
            print(f"Ошибка обработки эмоций: {e}")

    def _on_cardio_indexes(self, cardio, indexes: Cardio_Data):
        """Колбэк кардиоданных"""
        try:
            if indexes.metricsAvailable:
                self.current_heart_rate = indexes.heartRate
                
                # Вызываем колбэки
                for callback in self.heart_rate_callbacks:
                    callback(indexes.heartRate)
                    
        except Exception as e:
            print(f"Ошибка обработки кардиоданных: {e}")

    def _on_calibrated(self, calibrator, data):
        """Колбэк завершения калибровки"""
        print(f"Калибровка завершена")
        self.is_calibrated = True
        self.event_loop.call_soon_threadsafe(self.calibration_complete_event.set)

    async def connect_selected_device(self, timeout: int = 30) -> bool:
        """Подключение к выбранному устройству"""
        if not self.device:
            print("❌ Устройство не выбрано")
            return False
        
        try:
            print("🔗 Пытаемся подключиться к устройству...")
            
            # Настраиваем колбэк подключения
            self.device.set_on_connection_status_changed(self._on_connection_status_changed)
            
            # Пробуем подключиться (биполярный режим обычно лучше)
            self.device.connect(bipolarChannels=True)
            
            # Ждем подключения
            try:
                await asyncio.wait_for(self.device_connected_event.wait(), timeout=timeout)
            except asyncio.TimeoutError:
                print("⏱️  Таймаут подключения")
                return False
            
            print(f"✅ Успешно подключено к: {self.selected_device.name}")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка подключения: {e}")
            return False

    async def calibrate_device(self, timeout: int = 40):
        """Калибровка устройства"""
        try:
            if not self.device or not self.is_connected:
                raise Exception("Устройство не подключено")
            
            # Запускаем устройство
            self.device.start()
            print("Устройство запущено, начинаем калибровку...")
            
            # Инициализируем классификаторы
            self.emotions = Emotions(self.device, self.capsule_lib.get_lib())
            self.emotions.set_on_states_update(self._on_emotions_states)
            
            self.cardio = Cardio(self.device, self.capsule_lib.get_lib())
            self.cardio.set_on_indexes_update(self._on_cardio_indexes)
            
            # Создаем калибратор
            self.calibrator = Calibrator(self.device, self.capsule_lib.get_lib())
            self.calibrator.set_on_calibration_finished(self._on_calibrated)
            
            # Быстрая калибровка (30 секунд)
            self.calibrator.calibrate_quick()
            
            # Ждем завершения калибровки
            try:
                await asyncio.wait_for(self.calibration_complete_event.wait(), timeout=timeout)
            except asyncio.TimeoutError:
                raise Exception("Калибровка не завершена (таймаут)")
            
            print("Калибровка успешно завершена!")
            self.is_calibrated = True
            return True
            
        except Exception as e:
            print(f"Ошибка калибровки: {e}")
            return False

    async def start_streaming(self):
        """Запуск потоковой передачи данных"""
        if not self.is_connected or not self.device:
            raise Exception("Устройство не подключено")
        
        self.is_streaming = True
        print("Потоковая передача данных начата")
        
        # Обновляем device locator в фоне для получения данных
        while self.is_streaming:
            try:
                self.device_locator.update()
                await asyncio.sleep(0.1)  # 10 раз в секунду
            except Exception as e:
                print(f"Ошибка в потоке данных: {e}")
                break

    async def stop_streaming(self):
        """Остановка потоковой передачи"""
        self.is_streaming = False
        if self.device:
            try:
                self.device.stop()
            except:
                pass
        print("Потоковая передача остановлена")

    async def disconnect(self):
        """Отключение от устройства"""
        await self.stop_streaming()
        
        if self.device:
            try:
                self.device.disconnect()
                self.is_connected = False
                self.is_calibrated = False
                print("Устройство отключено")
            except Exception as e:
                print(f"Ошибка отключения: {e}")

    # Колбэки для данных
    def add_concentration_callback(self, callback: Callable[[float], None]):
        """Добавление колбэка для данных концентрации"""
        self.concentration_callbacks.append(callback)

    def add_heart_rate_callback(self, callback: Callable[[float], None]):
        """Добавление колбэка для данных пульса"""
        self.heart_rate_callbacks.append(callback)

    def add_stress_callback(self, callback: Callable[[float], None]):
        """Добавление колбэка для данных стресса"""
        self.stress_callbacks.append(callback)

    def add_focus_callback(self, callback: Callable[[float], None]):
        """Добавление колбэка для данных фокуса"""
        self.focus_callbacks.append(callback)

    def get_current_metrics(self) -> Dict[str, Any]:
        """Получение текущих метрик"""
        device_info = {}
        if self.selected_device:
            device_info = self.selected_device.to_dict()
        
        return {
            "concentration": self.current_concentration,
            "focus": self.current_focus,
            "stress": self.current_stress,
            "heart_rate": self.current_heart_rate,
            "is_calibrated": self.is_calibrated,
            "is_connected": self.is_connected,
            "is_streaming": self.is_streaming,
            "selected_device": device_info,
            "found_devices_count": len(self.found_devices)
        }