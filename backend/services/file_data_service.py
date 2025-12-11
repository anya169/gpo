import asyncio
import csv
import os
import time
from typing import List, Dict, Any, Callable, Optional
from pathlib import Path
import aiofiles
import re

class FileDataService:
    def __init__(self):
        self.is_streaming = False
        self.data_file = "C:/Users/Darya/AppData/Roaming/Capsule Data/Sessions/954c79d2-8094-4c87-90da-eda47e140fad/metrics.csv"
        self.stream_speed = 1.0
        self.concentration_callbacks: List[Callable] = []
        self.current_session_id = None
        self.data_points = []
        self.last_read_position = 0
        self.is_watching = False
        self.watch_task = None
        self.session_start_time = None
        self.session_stop_time = None
        
        # Создаем директорию если не существует
        file_path = Path(self.data_file)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Загружаем существующие данные
        self._load_existing_data()

    def _load_existing_data(self):
        """Загружает существующие данные из файла"""
        try:
            if os.path.exists(self.data_file) and os.path.getsize(self.data_file) > 0:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    # Пропускаем первую строку (Session start time)
                    start_line = f.readline()
                    if "Session start time" in start_line:
                        match = re.search(r'(\d{2}:\d{2}:\d{2})', start_line)
                        if match:
                            self.session_start_time = match.group(1)
                    
                    # Читаем заголовок
                    header = f.readline()
                    
                    self.data_points = []
                    reader = csv.reader(f)
                    
                    for row in reader:
                        if not row or len(row) < 2:
                            continue
                        
                        # Пропускаем служебные строки
                        first_col = str(row[0]).strip()
                        if first_col.startswith("Session") or first_col.startswith("IAPF Calibration") or first_col.startswith("Baseline Calibration"):
                            continue
                        
                        # Парсим данные
                        data_point = self._parse_csv_row(row)
                        if data_point:
                            self.data_points.append(data_point)
                    
                    # Сохраняем текущую позицию
                    self.last_read_position = f.tell()
                    print(f"Загружено {len(self.data_points)} существующих записей")
                    
                    # Извлекаем время начала сессии
                    self._extract_session_times()
                    
            else:
                print("Файл данных не существует или пуст.")
                self.data_points = []
                
        except Exception as e:
            print(f"Ошибка загрузки существующих данных: {e}")
            self.data_points = []

    def _extract_session_times(self):
        """Извлекает время начала и окончания сессии из файла"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    # Читаем первую строку (Session start time)
                    start_line = f.readline().strip()
                    if "Session start time" in start_line:
                        match = re.search(r'(\d{2}:\d{2}:\d{2})', start_line)
                        if match:
                            self.session_start_time = match.group(1)
                            print(f"Время начала сессии: {self.session_start_time}")
                    
                    # Ищем строку с окончанием сессии
                    content = f.read()
                    if "Session stop time" in content:
                        match = re.search(r'Session stop time,\s*(\d{2}:\d{2}:\d{2})', content)
                        if match:
                            self.session_stop_time = match.group(1)
                            print(f"Время окончания сессии: {self.session_stop_time}")
                            
        except Exception as e:
            print(f"Ошибка извлечения времени сессии: {e}")

    def _parse_csv_row(self, row: list) -> Optional[Dict[str, Any]]:
        try:
            if len(row) < 29:
                return None   
            mark = str(row[0]).strip()
            if 'm' not in str(row[1]) or 's' not in str(row[2]):
                return None
            # Извлекаем время
            minutes_str = str(row[1]).replace('m', '').strip()
            seconds_str = str(row[2]).replace('s', '').strip()
            try:
                minutes = int(float(minutes_str))
                seconds = int(float(seconds_str))
            except:
                return None
            # Парсим основные метрики
            try:
                concentration = float(row[10]) if row[10] else 0.0
                baseline_concentration = float(row[9]) if row[9] else 0.0
                fatigue_score = float(row[6]) if row[6] else 0.0
                alpha = float(row[20]) if row[20] else 0.0  
                beta = float(row[21]) if row[21] else 0.0  
                theta = float(row[19]) if row[19] else 0.0  
                relaxation = float(row[25]) if row[25] else 50.0  
                attention = float(row[27]) if row[27] else 50.0  
                cognitive_load = float(row[26]) if row[26] else 50.0 
                heart_rate = float(row[15]) if row[15] else 0.0  
                stress = float(row[16]) if row[16] else 0.0  

                data_point = {
                    "mark": mark,
                    "timestamp": f"{minutes:02d}:{seconds:02d}",
                    "total_seconds": minutes * 60 + seconds,
                    "concentration": concentration,
                    "baseline_concentration": baseline_concentration,
                    "fatigue_score": fatigue_score,
                    "alpha": alpha,
                    "beta": beta,
                    "theta": theta,
                    "heart_rate": heart_rate,
                    "stress": stress,
                    "attention": attention,
                    "cognitive_load": cognitive_load,
                    "relaxation": relaxation,
                    "relaxation_index": float(row[12]) if row[12] else 0.0,
                    "alpha_gravity": float(row[8]) if row[8] else 0.0,
                    "iapf": float(row[3]) if row[3] else 0.0,
                    "iaf": float(row[4]) if row[4] else 0.0,
                    "cognitive_control": float(row[28]) if len(row) > 28 and row[28] else 50.0,
                    "theta_peak": float(row[22]) if len(row) > 22 and row[22] else 0.0,
                    "alpha_peak": float(row[23]) if len(row) > 23 and row[23] else 0.0,
                    "beta_peak": float(row[24]) if len(row) > 24 and row[24] else 0.0,
                }
                
                return data_point
                
            except (ValueError, IndexError) as e:
                print(f"Ошибка парсинга: {e}")
                return None
                
        except Exception as e:
            print(f"Ошибка парсинга строки: {e}")
            return None

    async def _read_new_data(self):
        try:
            if not os.path.exists(self.data_file):
                return []
            
            async with aiofiles.open(self.data_file, 'r', encoding='utf-8') as f:
                # Перемещаемся к последней прочитанной позиции
                await f.seek(self.last_read_position)
                
                # Читаем все новые строки
                content = await f.read()
                
                if not content:
                    return []
                
                # Обновляем позицию
                self.last_read_position = await f.tell()
                
                # Парсим новые строки
                new_data_points = []
                lines = content.strip().split('\n')
                
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Парсим CSV строку
                    row = next(csv.reader([line]))
                    
                    if not row or len(row) < 3:
                        continue
                    
                    # Пропускаем служебные строки
                    first_col = str(row[0]).strip()
                    if first_col.startswith("Session") or first_col.startswith("IAPF Calibration") or first_col.startswith("Baseline Calibration"):
                        if "Session stop time" in first_col and len(row) > 1:
                            match = re.search(r'(\d{2}:\d{2}:\d{2})', str(row[1]))
                            if match:
                                self.session_stop_time = match.group(1)
                        continue
                    
                    # Парсим данные
                    data_point = self._parse_csv_row(row)
                    if data_point:
                        new_data_points.append(data_point)
                
                return new_data_points
                
        except Exception as e:
            print(f"Ошибка чтения новых данных: {e}")
            return []

    async def _watch_and_stream(self):
        while self.is_watching and self.is_streaming:
            try:
                # Проверяем, существует ли файл
                if not os.path.exists(self.data_file):
                    await asyncio.sleep(self.stream_speed)
                    continue
                
                # Читаем новые данные
                new_data = await self._read_new_data()
                
                if new_data:
                    print(f"Обнаружено {len(new_data)} новых записей")
                    
                    # Обрабатываем каждую новую запись
                    for data_point in new_data:
                        
                        data_point["data_index"] = len(self.data_points)
                        data_point["total_points"] = len(self.data_points) + 1
                        
                        self.data_points.append(data_point)
                        
                        for callback in self.concentration_callbacks:
                            try:
                                if asyncio.iscoroutinefunction(callback):
                                    await callback(data_point["concentration"], data_point)
                                else:
                                    callback(data_point["concentration"], data_point)
                            except Exception as e:
                                print(f"Ошибка в колбэке: {e}")
                
                await asyncio.sleep(self.stream_speed)
                
            except Exception as e:
                print(f"Ошибка в процессе отслеживания: {e}")
                await asyncio.sleep(self.stream_speed)

    def add_concentration_callback(self, callback: Callable):
        """Добавляет колбэк для получения данных концентрации"""
        self.concentration_callbacks.append(callback)

    async def start_streaming(self, session_id: int):
        """Запускает потоковую передачу данных в реальном времени"""
        if self.is_streaming:
            print("Стриминг уже запущен")
            return
        
        self.is_streaming = True
        self.is_watching = True
        self.current_session_id = session_id
        
        print(f"Запуск стриминга реальных данных (session_id: {session_id})")
        
        # Запускаем отслеживание файла
        self.watch_task = asyncio.create_task(self._watch_and_stream())
        print("Отслеживание файла запущено")

    async def stop_streaming(self):
        """Останавливает потоковую передачу"""
        self.is_streaming = False
        self.is_watching = False
        
        if self.watch_task:
            self.watch_task.cancel()
            try:
                await self.watch_task
            except asyncio.CancelledError:
                pass
        
        print("Стриминг остановлен")

    def set_stream_speed(self, speed: float):
        """Устанавливает скорость проверки файла (секунды между проверками)"""
        self.stream_speed = speed
        print(f"Скорость проверки установлена: {speed} секунд")

    async def get_current_metrics(self) -> Dict[str, Any]:
        """Возвращает текущие метрики (последнюю запись)"""
        if self.data_points:
            last_data = self.data_points[-1]
            
            return {
                "concentration": last_data.get("concentration", 0.0),
                "focus": last_data.get("focus", 50.0),
                "stress": last_data.get("stress", 0.0),
                "heart_rate": last_data.get("heart_rate", 0),
                "alpha": last_data.get("alpha", 0.0),
                "beta": last_data.get("beta", 0.0),
                "theta": last_data.get("theta", 0.0),
                "fatigue_score": last_data.get("fatigue_score", 0.0),
                "relaxation_index": last_data.get("relaxation_index", 0.0),
                "mark": last_data.get("mark", "0"),
                "name": last_data.get("name", "Малахов"),
                "timestamp": last_data.get("timestamp", "00:00"),
                "attention": last_data.get("attention", 50.0),
                "cognitive_load": last_data.get("cognitive_load", 50.0),
                "relaxation": last_data.get("relaxation", 50.0),
                "cognitive_control": last_data.get("cognitive_control", 50.0),
                "is_streaming": self.is_streaming,
                "session_id": self.current_session_id,
                "current_index": len(self.data_points) - 1,
                "total_points": len(self.data_points),
                "session_start_time": self.session_start_time,
                "session_stop_time": self.session_stop_time,
                "total_seconds": last_data.get("total_seconds", 0)
            }
            
        return {
            "concentration": 0.0,
            "focus": 0.0,
            "stress": 0.0,
            "heart_rate": 0,
            "alpha": 0.0,
            "beta": 0.0,
            "theta": 0.0,
            "fatigue_score": 0.0,
            "relaxation_index": 0.0,
            "mark": "0",
            "name": "Малахов",
            "timestamp": "00:00",
            "is_streaming": False,
            "session_id": None,
            "current_index": 0,
            "total_points": 0,
            "session_start_time": self.session_start_time,
            "session_stop_time": self.session_stop_time,
            "total_seconds": 0
        }

    def get_all_data(self) -> List[Dict[str, Any]]:
        """Возвращает все загруженные данные"""
        return self.data_points

    def get_recent_data(self, count: int = 10) -> List[Dict[str, Any]]:
        """Возвращает последние N записей"""
        return self.data_points[-count:] if self.data_points else []

    def get_session_info(self) -> Dict[str, Any]:
        """Возвращает информацию о сессии"""
        return {
            "start_time": self.session_start_time,
            "stop_time": self.session_stop_time,
            "duration_seconds": self.data_points[-1]["total_seconds"] if self.data_points else 0,
            "data_points_count": len(self.data_points),
            "file_path": self.data_file
        }

    async def start_file_watching(self):
        """Запускает отслеживание файла для реального времени"""
        if not self.is_watching:
            self.is_watching = True
            print("Запущено отслеживание файла в реальном времени")
            self.watch_task = asyncio.create_task(self._watch_and_stream())
        
    async def stop_file_watching(self):
        """Останавливает отслеживание файла"""
        self.is_watching = False
        if self.watch_task:
            self.watch_task.cancel()
            try:
                await self.watch_task
            except asyncio.CancelledError:
                pass
        print("Остановлено отслеживание файла")

# Глобальный экземпляр сервиса
file_data_service = FileDataService()