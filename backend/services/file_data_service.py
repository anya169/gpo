import asyncio
import json
import csv
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable
import os

class FileDataService:
    def __init__(self):
        self.is_streaming = False
        self.data_file = "Малахов.xlsx"
        self.stream_speed = 1.0
        self.concentration_callbacks: List[Callable] = []
        self.current_session_id = None
        self.current_data_index = 0
        self.data_points = []
        
        self._load_excel_data()

    def _load_excel_data(self):
        """Загружает данные из Excel файла"""
        try:
            df = pd.read_excel(self.data_file, sheet_name='Sheet1')
            
            self.data_points = []
            for index, row in df.iterrows():
                concentration = row.get('Concentration Index', 0.0)
                if pd.isna(concentration):
                    concentration = 0.0
                
                data_point = {
                    "timestamp": f"00:{index:02d}:00",
                    "concentration": float(concentration),
                    "focus": float(row.get('Focus', 0.0)) if not pd.isna(row.get('Focus')) else 50.0,
                    "stress": float(row.get('Stress', 0.0)) if not pd.isna(row.get('Stress')) else 50.0,
                    "heart_rate": 70,
                    "alpha": float(row.get('Alpha', 0.0)) if not pd.isna(row.get('Alpha')) else 0.0,
                    "beta": float(row.get('Beta', 0.0)) if not pd.isna(row.get('Beta')) else 0.0,
                    "theta": float(row.get('Theta', 0.0)) if not pd.isna(row.get('Theta')) else 0.0,
                    "fatigue_score": float(row.get('Fatigue Score', 0.0)) if not pd.isna(row.get('Fatigue Score')) else 0.0,
                    "relaxation_index": float(row.get('Relaxation Index', 0.0)) if not pd.isna(row.get('Relaxation Index')) else 0.0,
                    "mark": row.get('mark', 'без практики'),
                    "name": row.get('name', 'Малахов')
                }
                self.data_points.append(data_point)
            
            print(f"Загружено {len(self.data_points)} точек данных из Excel файла")
            
        except Exception as e:
            print(f"Ошибка загрузки Excel файла: {e}")
            self._create_sample_data()

    def add_concentration_callback(self, callback: Callable):
        """Добавляет колбэк для получения данных концентрации"""
        self.concentration_callbacks.append(callback)

    async def start_streaming(self, session_id: int):
        """Запускает потоковую передачу данных из файла"""
        if self.is_streaming:
            return
        
        self.is_streaming = True
        self.current_session_id = session_id
        self.current_data_index = 0
        
        # Запускаем потоковую передачу
        asyncio.create_task(self._stream_data())

    async def stop_streaming(self):
        """Останавливает потоковую передачу"""
        self.is_streaming = False

    async def _stream_data(self):
        """Потоковая передача данных с заданной скоростью"""
        while self.is_streaming and self.data_points:
            if self.current_data_index >= len(self.data_points):
                self.current_data_index = 0  # Начинаем сначала когда дошли до конца
                
            data_point = self.data_points[self.current_data_index]
            
            # Вызываем все колбэки
            for callback in self.concentration_callbacks:
                await callback(data_point["concentration"], {
                    "heart_rate": data_point["heart_rate"],
                    "stress": data_point["stress"],
                    "focus": data_point["focus"],
                    "alpha": data_point["alpha"],
                    "beta": data_point["beta"],
                    "theta": data_point["theta"],
                    "fatigue_score": data_point["fatigue_score"],
                    "relaxation_index": data_point["relaxation_index"],
                    "mark": data_point["mark"],
                    "name": data_point["name"],
                    "timestamp": data_point["timestamp"],
                    "data_index": self.current_data_index,
                    "total_points": len(self.data_points)
                })
            
            self.current_data_index += 1
            await asyncio.sleep(self.stream_speed)

    def set_stream_speed(self, speed: float):
        """Устанавливает скорость потоковой передачи (секунды между обновлениями)"""
        self.stream_speed = speed

    async def get_current_metrics(self) -> Dict[str, Any]:
        """Возвращает текущие метрики (для API)"""
        if self.data_points and self.current_data_index > 0:
            current_index = min(self.current_data_index - 1, len(self.data_points) - 1)
            data_point = self.data_points[current_index]
            
            return {
                "concentration": data_point["concentration"],
                "heart_rate": data_point["heart_rate"],
                "stress": data_point["stress"],
                "focus": data_point["focus"],
                "alpha": data_point["alpha"],
                "beta": data_point["beta"],
                "theta": data_point["theta"],
                "fatigue_score": data_point["fatigue_score"],
                "relaxation_index": data_point["relaxation_index"],
                "mark": data_point["mark"],
                "name": data_point["name"],
                "is_streaming": self.is_streaming,
                "session_id": self.current_session_id,
                "current_index": current_index,
                "total_points": len(self.data_points)
            }
            
        return {
            "concentration": 0.0,
            "heart_rate": 0,
            "stress": 0,
            "focus": 0.0,
            "is_streaming": False,
            "session_id": None
        }

    def get_all_data(self) -> List[Dict[str, Any]]:
        """Возвращает все загруженные данные"""
        return self.data_points

file_data_service = FileDataService()