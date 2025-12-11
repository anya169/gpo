# utils/statistics_utils.py
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
from collections import defaultdict
import calendar

class StatisticsUtils:
    @staticmethod
    def calculate_session_duration(session_start: datetime, session_end: Optional[datetime] = None) -> float:
        """Рассчитывает длительность сессии в минутах"""
        end_time = session_end or datetime.now()
        duration = end_time - session_start
        return duration.total_seconds() / 60

    @staticmethod
    def calculate_daily_stats(sessions: List[Any], target_date: date) -> Dict[str, Any]:
        """Вычисляет статистику за день"""
        if not sessions:
            return {
                "date": target_date.isoformat(),
                "total_sessions": 0,
                "total_duration_minutes": 0,
                "avg_concentration": 0,
                "focus_dips_count": 0,
                "sessions": []
            }
        
        total_duration = 0
        total_concentration = 0
        total_focus_dips = 0
        sessions_data = []
        
        for session in sessions:
            # Вычисляем длительность сессии
            duration_minutes = StatisticsUtils.calculate_session_duration(
                session.start_time, session.end_time
            )
            
            total_duration += duration_minutes
            total_concentration += session.avg_concentration or 0
            total_focus_dips += session.focus_dips_count or 0
            
            sessions_data.append({
                "session_id": session.session_id,
                "start_time": session.start_time.isoformat(),
                "end_time": session.end_time.isoformat() if session.end_time else None,
                "duration_minutes": round(duration_minutes, 2),
                "avg_concentration": session.avg_concentration,
                "focus_dips_count": session.focus_dips_count,
                "baseline_concentration": session.baseline_concentration,
                "is_active": session.is_active
            })
        
        avg_concentration = total_concentration / len(sessions) if sessions else 0
        
        return {
            "date": target_date.isoformat(),
            "total_sessions": len(sessions),
            "total_duration_minutes": round(total_duration, 2),
            "avg_concentration": round(avg_concentration, 2),
            "focus_dips_count": total_focus_dips,
            "sessions": sessions_data
        }

    @staticmethod
    def calculate_weekly_stats(sessions: List[Any], week_start: date, week_end: date) -> Dict[str, Any]:
        """Вычисляет статистику за неделю"""
        if not sessions:
            return {
                "week_start": week_start.isoformat(),
                "week_end": week_end.isoformat(),
                "total_sessions": 0,
                "total_duration_minutes": 0,
                "avg_concentration": 0,
                "focus_dips_count": 0,
                "days_with_sessions": 0
            }
        
        # Группируем по дням
        sessions_by_day = defaultdict(list)
        for session in sessions:
            day = session.start_time.date()
            sessions_by_day[day].append(session)
        
        total_sessions = len(sessions)
        total_duration = 0
        total_concentration = 0
        total_focus_dips = 0
        
        for day_sessions in sessions_by_day.values():
            for session in day_sessions:
                duration_minutes = StatisticsUtils.calculate_session_duration(
                    session.start_time, session.end_time
                )
                
                total_duration += duration_minutes
                total_concentration += session.avg_concentration or 0
                total_focus_dips += session.focus_dips_count or 0
        
        avg_concentration = total_concentration / total_sessions if total_sessions > 0 else 0
        
        return {
            "week_start": week_start.isoformat(),
            "week_end": week_end.isoformat(),
            "total_sessions": total_sessions,
            "total_duration_minutes": round(total_duration, 2),
            "avg_concentration": round(avg_concentration, 2),
            "focus_dips_count": total_focus_dips,
            "days_with_sessions": len(sessions_by_day)
        }

    @staticmethod
    def get_week_boundaries(target_date: date) -> tuple[date, date]:
        """Получает начало и конец недели для даты"""
        week_start = target_date - timedelta(days=target_date.weekday())
        week_end = week_start + timedelta(days=6)
        return week_start, week_end

    @staticmethod
    def calculate_exercise_effectiveness(concentration_before: float, concentration_after: float) -> str:
        """Определяет эффективность упражнения"""
        if concentration_before is None or concentration_after is None:
            return "neutral"
        
        improvement = concentration_after - concentration_before
        if improvement > 10:
            return "high"
        elif improvement > 5:
            return "medium"
        elif improvement < -5:
            return "low"
        else:
            return "neutral"

    @staticmethod
    def format_session_for_response(session: Any) -> Dict[str, Any]:
        """Форматирует сессию для ответа API"""
        duration_minutes = StatisticsUtils.calculate_session_duration(
            session.start_time, session.end_time
        )
        
        return {
            "session_id": session.session_id,
            "start_time": session.start_time.isoformat(),
            "end_time": session.end_time.isoformat() if session.end_time else None,
            "duration_minutes": round(duration_minutes, 2),
            "avg_concentration": session.avg_concentration,
            "focus_dips_count": session.focus_dips_count,
            "baseline_concentration": session.baseline_concentration,
            "is_active": session.is_active
        }