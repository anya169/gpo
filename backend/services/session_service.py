# session_service.py (обновленная версия)
from datetime import datetime
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Dict, Any

from models import Session, Concentration, Exercise
from utils.statistics_utils import StatisticsUtils

class SessionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.utils = StatisticsUtils()

    async def create_session(self, user_id: int) -> Dict[str, Any]:
        stmt = select(Session).where(
            Session.user_id == user_id,
            Session.is_active == True
        )
        result = await self.db.execute(stmt)
        active_session = result.scalar_one_or_none()
        
        if active_session:
            await self.end_session(active_session.session_id)

        session = Session(user_id=user_id)
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        
        return {
            "session_id": session.session_id,
            "start_time": session.start_time,
            "user_id": user_id
        }

    async def end_session(self, session_id: int) -> Dict[str, Any]:
        stmt = select(Session).where(Session.session_id == session_id)
        result = await self.db.execute(stmt)
        session = result.scalar_one()

        stats = await self._calculate_session_stats(session_id)
        
        session.end_time = datetime.now()
        session.is_active = False
        session.avg_concentration = stats["avg_concentration"]
        session.focus_dips_count = stats["focus_dips_count"]
        
        await self.db.commit()
        
        return {
            "session_id": session_id,
            "duration_minutes": stats["duration_minutes"],
            "avg_concentration": stats["avg_concentration"],
            "focus_dips_count": stats["focus_dips_count"],
            "exercises_completed": stats["exercises_completed"]
        }

    async def _calculate_session_stats(self, session_id: int) -> Dict[str, Any]:
        """Вычисляет статистику сессии"""
        # Средняя концентрация
        avg_stmt = select(func.avg(Concentration.value)).where(
            Concentration.session_id == session_id
        )
        avg_result = await self.db.execute(avg_stmt)
        avg_concentration = avg_result.scalar() or 0.0

        # Количество упражнений (срабатываний детектора)
        exercises_stmt = select(func.count(Exercise.id)).where(
            Exercise.session_id == session_id
        )
        exercises_result = await self.db.execute(exercises_stmt)
        exercises_count = exercises_result.scalar() or 0

        # Количество завершенных упражнений
        completed_exercises_stmt = select(func.count(Exercise.id)).where(
            Exercise.session_id == session_id,
            Exercise.completed == True
        )
        completed_result = await self.db.execute(completed_exercises_stmt)
        completed_count = completed_result.scalar() or 0

        # Длительность сессии
        session_stmt = select(Session.start_time, Session.end_time).where(
            Session.session_id == session_id
        )
        session_result = await self.db.execute(session_stmt)
        session_data = session_result.first()
        
        duration_minutes = 0
        if session_data:
            start_time, end_time = session_data
            duration_minutes = self.utils.calculate_session_duration(
                start_time, end_time or datetime.now()
            )

        return {
            "avg_concentration": round(avg_concentration, 2),
            "focus_dips_count": exercises_count,
            "exercises_completed": completed_count,
            "duration_minutes": round(duration_minutes, 2)
        }

    async def get_active_session(self, user_id: int) -> Dict[str, Any]:
        stmt = select(Session).where(
            Session.user_id == user_id,
            Session.is_active == True
        )
        result = await self.db.execute(stmt)
        session = result.scalar_one_or_none()
        
        if not session:
            return {"has_active_session": False}
    
        stats = await self._calculate_session_stats(session.session_id)
        
        return {
            "has_active_session": True,
            "session_id": session.session_id,
            "start_time": session.start_time,
            "baseline_concentration": session.baseline_concentration,
            "stats": stats
        }

    async def get_user_sessions(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        stmt = select(Session).where(
            Session.user_id == user_id
        ).order_by(Session.start_time.desc()).limit(limit)
        
        result = await self.db.execute(stmt)
        sessions = result.scalars().all()
        
        sessions_data = []
        for session in sessions:
            stats = await self._calculate_session_stats(session.session_id)
            sessions_data.append({
                "session_id": session.session_id,
                "start_time": session.start_time,
                "end_time": session.end_time,
                "is_active": session.is_active,
                "baseline_concentration": session.baseline_concentration,
                "stats": stats
            })
        
        return sessions_data