import asyncio
import math 
from datetime import datetime, timedelta
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models import Session, Concentration
from .neiry_service import NeiryHeadbendService

class CalibrationService:
    def __init__(self, db: AsyncSession, neiry_service: NeiryHeadbendService):
        self.db = db
        self.neiry_service = neiry_service
        self.calibration_data = []
        self.is_calibrating = False
        self.calibration_start_time = None
        self.calibration_duration = 120 
        self.progress_callbacks = []

    async def start_calibration(self, session_id: int, duration: int = 120) -> Dict[str, Any]:
        if self.is_calibrating:
            return {"success": False, "error": "Калибровка уже выполняется"}
        
        self.is_calibrating = True
        self.calibration_data = []
        self.calibration_start_time = datetime.now()
        self.calibration_duration = duration
        self.session_id = session_id
        
        await self.neiry_service.start_concentration_stream(self._handle_calibration_data)
        
        return {
            "success": True,
            "message": "Калибровка начата. Сядьте удобно и закройте глаза на 2 минуты.",
            "duration_seconds": duration,
            "instructions": [
                "Сядьте в удобное положение",
                "Закройте глаза и расслабьтесь",
                "Старайтесь не двигаться в течение 2 минут",
                "Дышите спокойно и равномерно"
            ]
        }

    async def _handle_calibration_data(self, concentration_value: float):
        if self.is_calibrating:
            data_point = {
                "value": concentration_value,
                "timestamp": datetime.now()
            }
            self.calibration_data.append(data_point)
            
            progress = await self.get_calibration_progress(self.session_id)
            for callback in self.progress_callbacks:
                await callback(progress)

    def _calculate_std_deviation(self, values: List[float]) -> float:
        if len(values) < 2:
            return 0.0
        
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return math.sqrt(variance)

    async def get_calibration_progress(self, session_id: int) -> Dict[str, Any]:
        if not self.is_calibrating:
            return {"is_active": False}
        
        elapsed = (datetime.now() - self.calibration_start_time).total_seconds()
        progress_percent = min(100, (elapsed / self.calibration_duration) * 100)
        
        current_stats = {}
        if self.calibration_data:
            values = [data["value"] for data in self.calibration_data]
            current_stats = {
                "current_value": round(values[-1], 2),
                "data_points": len(values),
                "current_avg": round(sum(values) / len(values), 2),
                "min_value": round(min(values), 2),
                "max_value": round(max(values), 2)
            }
        
        return {
            "is_active": True,
            "progress_percent": round(progress_percent, 1),
            "elapsed_seconds": round(elapsed),
            "remaining_seconds": max(0, self.calibration_duration - elapsed),
            "data_points": len(self.calibration_data),
            "current_stats": current_stats
        }

    async def complete_calibration(self, session_id: int) -> Dict[str, Any]:
        if not self.is_calibrating:
            raise Exception("Калибровка не выполняется")
        
        self.is_calibrating = False
        
        if not self.calibration_data:
            raise Exception("Нет данных калибровки")
        
        # Рассчитываем среднюю концентрацию как базовую линию
        values = [data["value"] for data in self.calibration_data]
        baseline = sum(values) / len(values)
        
        stmt = select(Session).where(Session.session_id == session_id)
        result = await self.db.execute(stmt)
        session = result.scalar_one()
        
        session.baseline_concentration = baseline
        
        for data in self.calibration_data:
            concentration = Concentration(
                session_id=session_id,
                value=data["value"],
                time=data["timestamp"],
                is_calibration=True
            )
            self.db.add(concentration)
        
        await self.db.commit()
        
        stats = {
            "baseline_concentration": round(baseline, 2),
            "data_points": len(self.calibration_data),
            "min_value": round(min(values), 2),
            "max_value": round(max(values), 2),
            "std_deviation": round(self._calculate_std_deviation(values), 2)
        }
        
        return {
            "success": True,
            "session_id": session_id,
            "baseline_concentration": baseline,
            "stats": stats,
            "message": f"Калибровка завершена. Базовая линия: {baseline:.2f}"
        }

    def add_progress_callback(self, callback):
        self.progress_callbacks.append(callback)