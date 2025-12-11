# service.py (добавляем импорт в начало файла)
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc, asc
from collections import defaultdict
import calendar  

from models import Session, Concentration, Exercise
from utils.statistics_utils import StatisticsUtils

class StatisticsService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.utils = StatisticsUtils()

    async def get_today_stats(self, user_id: int) -> Dict[str, Any]:
        """Статистика за сегодня"""
        today = date.today()
        
        stmt = select(Session).where(
            Session.user_id == user_id,
            func.date(Session.start_time) == today
        ).order_by(desc(Session.start_time))
        
        result = await self.db.execute(stmt)
        sessions = result.scalars().all()
        
        return self.utils.calculate_daily_stats(sessions, today)

    async def get_current_week_stats(self, user_id: int) -> Dict[str, Any]:
        """Статистика за текущую неделю"""
        today = date.today()
        week_start, week_end = self.utils.get_week_boundaries(today)
        
        stmt = select(Session).where(
            Session.user_id == user_id,
            func.date(Session.start_time) >= week_start,
            func.date(Session.start_time) <= week_end
        ).order_by(Session.start_time)
        
        result = await self.db.execute(stmt)
        sessions = result.scalars().all()
        
        stats = self.utils.calculate_weekly_stats(sessions, week_start, week_end)
        
        # Добавляем ежедневную статистику
        daily_stats = await self._get_daily_stats_for_week(user_id, week_start, week_end)
        stats["daily_breakdown"] = daily_stats
        
        return stats

    async def get_daily_statistics(self, user_id: int, target_date: date) -> Dict[str, Any]:
        """Подробная статистика за конкретный день"""
        stmt = select(Session).where(
            Session.user_id == user_id,
            func.date(Session.start_time) == target_date
        ).order_by(desc(Session.start_time))
        
        result = await self.db.execute(stmt)
        sessions = result.scalars().all()
        
        stats = self.utils.calculate_daily_stats(sessions, target_date)
        
        # Добавляем почасовую статистику концентрации
        hourly_stats = await self._get_hourly_concentration(user_id, target_date)
        stats["hourly_concentration"] = hourly_stats
        
        return stats

    async def get_weekly_statistics(self, user_id: int, week_start: date) -> Dict[str, Any]:
        """Подробная статистика за конкретную неделю"""
        week_end = week_start + timedelta(days=6)
        
        stmt = select(Session).where(
            Session.user_id == user_id,
            func.date(Session.start_time) >= week_start,
            func.date(Session.start_time) <= week_end
        ).order_by(Session.start_time)
        
        result = await self.db.execute(stmt)
        sessions = result.scalars().all()
        
        stats = self.utils.calculate_weekly_stats(sessions, week_start, week_end)
        
        # Добавляем ежедневную статистику для графика
        daily_stats = await self._get_daily_stats_for_week(user_id, week_start, week_end)
        stats["daily_breakdown"] = daily_stats
        
        return stats

    async def get_session_history(self, user_id: int, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        """История сессий пользователя"""
        stmt = select(Session).where(
            Session.user_id == user_id,
            Session.is_active == False
        ).order_by(desc(Session.start_time)).offset(offset).limit(limit)
        
        result = await self.db.execute(stmt)
        sessions = result.scalars().all()
        
        sessions_data = []
        for session in sessions:
            # Получаем концентрацию для сессии
            conc_stmt = select(Concentration).where(
                Concentration.session_id == session.session_id
            ).order_by(Concentration.time).limit(100)
            
            conc_result = await self.db.execute(conc_stmt)
            concentrations = conc_result.scalars().all()
            
            # Получаем упражнения
            ex_stmt = select(Exercise).where(
                Exercise.session_id == session.session_id
            )
            ex_result = await self.db.execute(ex_stmt)
            exercises = ex_result.scalars().all()
            
            sessions_data.append({
                "session_id": session.session_id,
                "start_time": session.start_time.isoformat(),
                "end_time": session.end_time.isoformat() if session.end_time else None,
                "duration_minutes": round(self.utils.calculate_session_duration(
                    session.start_time, session.end_time
                ), 2),
                "avg_concentration": session.avg_concentration,
                "focus_dips_count": session.focus_dips_count,
                "baseline_concentration": session.baseline_concentration,
                "concentration_samples": len(concentrations),
                "exercises_count": len(exercises),
                "completed_exercises": sum(1 for ex in exercises if ex.completed)
            })
        
        return sessions_data

    async def get_session_detailed(self, user_id: int, session_id: int) -> Optional[Dict[str, Any]]:
        """Подробная статистика конкретной сессии"""
        # Проверяем, что сессия принадлежит пользователю
        stmt = select(Session).where(
            Session.session_id == session_id,
            Session.user_id == user_id
        )
        
        result = await self.db.execute(stmt)
        session = result.scalar_one_or_none()
        
        if not session:
            return None
        
        # Получаем все данные концентрации
        conc_stmt = select(Concentration).where(
            Concentration.session_id == session_id
        ).order_by(Concentration.time)
        
        conc_result = await self.db.execute(conc_stmt)
        concentrations = conc_result.scalars().all()
        
        # Получаем все упражнения
        ex_stmt = select(Exercise).where(
            Exercise.session_id == session_id
        ).order_by(Exercise.start_time)
        
        ex_result = await self.db.execute(ex_stmt)
        exercises = ex_result.scalars().all()
        
        # Вычисляем статистику по упражнениям
        exercises_stats = []
        for exercise in exercises:
            effectiveness = self.utils.calculate_exercise_effectiveness(
                exercise.concentration_before, exercise.concentration_after
            )
            
            duration = 0
            if exercise.end_time:
                duration = (exercise.end_time - exercise.start_time).total_seconds()
            
            exercises_stats.append({
                "exercise_id": exercise.id,
                "type": exercise.exercise_type,
                "start_time": exercise.start_time.isoformat(),
                "end_time": exercise.end_time.isoformat() if exercise.end_time else None,
                "duration_seconds": duration,
                "completed": exercise.completed,
                "concentration_before": exercise.concentration_before,
                "concentration_after": exercise.concentration_after,
                "effectiveness": effectiveness
            })
        
        # Подготавливаем данные концентрации для графика
        concentration_data = [
            {
                "timestamp": conc.time.isoformat(),
                "value": conc.value,
                "is_calibration": conc.is_calibration
            }
            for conc in concentrations
        ]
        
        return {
            "session_id": session.session_id,
            "start_time": session.start_time.isoformat(),
            "end_time": session.end_time.isoformat() if session.end_time else None,
            "duration_minutes": round(self.utils.calculate_session_duration(
                session.start_time, session.end_time
            ), 2),
            "avg_concentration": session.avg_concentration,
            "focus_dips_count": session.focus_dips_count,
            "baseline_concentration": session.baseline_concentration,
            "is_active": session.is_active,
            "concentration_data": concentration_data,
            "exercises": exercises_stats,
            "total_concentration_samples": len(concentrations),
            "total_exercises": len(exercises),
            "completed_exercises": sum(1 for ex in exercises if ex.completed)
        }

    async def get_adjacent_sessions(self, user_id: int, session_id: int) -> Tuple[Optional[int], Optional[int]]:
        """Получает ID предыдущей и следующей сессии"""
        # Получаем текущую сессию
        current_stmt = select(Session.start_time).where(
            Session.session_id == session_id,
            Session.user_id == user_id
        )
        current_result = await self.db.execute(current_stmt)
        current_time = current_result.scalar_one_or_none()
        
        if not current_time:
            return None, None
        
        # Предыдущая сессия (более поздняя по времени)
        prev_stmt = select(Session.session_id).where(
            Session.user_id == user_id,
            Session.start_time > current_time
        ).order_by(asc(Session.start_time)).limit(1)
        
        prev_result = await self.db.execute(prev_stmt)
        prev_session = prev_result.scalar_one_or_none()
        
        # Следующая сессия (более ранняя по времени)
        next_stmt = select(Session.session_id).where(
            Session.user_id == user_id,
            Session.start_time < current_time
        ).order_by(desc(Session.start_time)).limit(1)
        
        next_result = await self.db.execute(next_stmt)
        next_session = next_result.scalar_one_or_none()
        
        return prev_session, next_session

    async def get_statistics_range(self, user_id: int, start_date: date, end_date: date) -> Dict[str, Any]:
        """Статистика за произвольный период"""
        stmt = select(Session).where(
            Session.user_id == user_id,
            func.date(Session.start_time) >= start_date,
            func.date(Session.start_time) <= end_date
        ).order_by(Session.start_time)
        
        result = await self.db.execute(stmt)
        sessions = result.scalars().all()
        
        # Группируем по дням
        daily_stats = {}
        current_date = start_date
        
        while current_date <= end_date:
            day_sessions = [s for s in sessions if s.start_time.date() == current_date]
            daily_stats[current_date.isoformat()] = self.utils.calculate_daily_stats(day_sessions, current_date)
            current_date += timedelta(days=1)
        
        # Общая статистика за период
        total_sessions = len(sessions)
        total_duration = sum(
            self.utils.calculate_session_duration(s.start_time, s.end_time or datetime.now())
            for s in sessions
        ) if sessions else 0
        
        total_concentration = sum(s.avg_concentration or 0 for s in sessions)
        total_focus_dips = sum(s.focus_dips_count or 0 for s in sessions)
        
        avg_concentration = total_concentration / total_sessions if total_sessions > 0 else 0
        
        return {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "total_sessions": total_sessions,
            "total_duration_minutes": round(total_duration, 2),
            "avg_concentration": round(avg_concentration, 2),
            "focus_dips_count": total_focus_dips,
            "daily_breakdown": daily_stats
        }

    async def _get_hourly_concentration(self, user_id: int, target_date: date) -> List[Dict[str, Any]]:
        """Получает почасовую статистику концентрации"""
        hourly_stats = []
        
        for hour in range(24):
            hour_start = datetime.combine(target_date, datetime.min.time()) + timedelta(hours=hour)
            hour_end = hour_start + timedelta(hours=1)
            
            # Получаем все концентрации за этот час
            stmt = select(Concentration.value).join(Session).where(
                Session.user_id == user_id,
                Concentration.time >= hour_start,
                Concentration.time < hour_end
            )
            
            result = await self.db.execute(stmt)
            values = result.scalars().all()
            
            avg_value = sum(values) / len(values) if values else 0
            
            hourly_stats.append({
                "hour": hour,
                "hour_label": f"{hour:02d}:00",
                "avg_concentration": round(avg_value, 2),
                "samples_count": len(values)
            })
        
        return hourly_stats

    async def _get_daily_stats_for_week(self, user_id: int, week_start: date, week_end: date) -> List[Dict[str, Any]]:
        """Получает ежедневную статистику для недели"""
        daily_stats = []
        
        current_date = week_start
        while current_date <= week_end:
            stmt = select(Session).where(
                Session.user_id == user_id,
                func.date(Session.start_time) == current_date
            )
            
            result = await self.db.execute(stmt)
            day_sessions = result.scalars().all()
            
            stats = self.utils.calculate_daily_stats(day_sessions, current_date)
            stats["day_name"] = calendar.day_name[current_date.weekday()]
            stats["day_number"] = current_date.day
            
            daily_stats.append(stats)
            current_date += timedelta(days=1)
        
        return daily_stats