import asyncio
from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from models import Concentration, Session

class ConcentrationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def add_concentration_data(self, session_id: int, value: float) -> Dict[str, Any]:
        concentration = Concentration(
            session_id=session_id,
            value=value,
            time=datetime.now()
        )
        self.db.add(concentration)
        await self.db.commit()
        await self.db.refresh(concentration)
        
        detection_triggered = await self._check_concentration_dip(session_id, value)
        
        return {
            "concentration_id": concentration.id,
            "session_id": session_id,
            "value": value,
            "timestamp": concentration.time,
            "detection_triggered": detection_triggered,
            "current_value": value
        }

    async def _check_concentration_dip(self, session_id: int, current_value: float) -> bool:
        """Проверка падения концентрации ниже базовой линии"""
        stmt = select(Session.baseline_concentration).where(Session.session_id == session_id)
        result = await self.db.execute(stmt)
        baseline = result.scalar()

        if baseline and current_value < (baseline * 0.7):  # Падение на 30%
            return True
        return False

    async def set_baseline_concentration(self, session_id: int, baseline: float):
        stmt = select(Session).where(Session.session_id == session_id)
        result = await self.db.execute(stmt)
        session = result.scalar_one()
        
        session.baseline_concentration = baseline
        await self.db.commit()

    async def get_concentration_history(self, session_id: int, limit: int = 100) -> List[Dict[str, Any]]:
        stmt = select(Concentration).where(
            Concentration.session_id == session_id
        ).order_by(Concentration.time.desc()).limit(limit)
        
        result = await self.db.execute(stmt)
        concentrations = result.scalars().all()
        
        return [
            {
                "id": conc.id,
                "value": conc.value,
                "timestamp": conc.time.isoformat(),
                "is_calibration": conc.is_calibration
            }
            for conc in reversed(concentrations)  
        ]