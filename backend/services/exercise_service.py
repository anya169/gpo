# exercise_service.py (обновленная версия)
from datetime import datetime
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict, Any

from models import Exercise, Session, Concentration
from utils.statistics_utils import StatisticsUtils

class ExerciseService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.utils = StatisticsUtils()

    async def start_exercise(self, session_id: int, exercise_type: str) -> Dict:
        # Получаем текущую концентрацию
        conc_stmt = select(Concentration.value).where(
            Concentration.session_id == session_id
        ).order_by(Concentration.time.desc()).limit(1)
        
        conc_result = await self.db.execute(conc_stmt)
        concentration_before = conc_result.scalar()

        exercise = Exercise(
            session_id=session_id,
            exercise_type=exercise_type,
            concentration_before=concentration_before
        )
        
        self.db.add(exercise)
        await self.db.commit()
        await self.db.refresh(exercise)

        return {
            "exercise_id": exercise.id,
            "type": exercise_type,
            "start_time": exercise.start_time,
            "concentration_before": concentration_before
        }

    async def complete_exercise(self, exercise_id: int):
        stmt = select(Exercise).where(Exercise.id == exercise_id)
        result = await self.db.execute(stmt)
        exercise = result.scalar_one()

        # Получаем концентрацию после упражнения
        conc_after_stmt = select(Concentration.value).where(
            Concentration.session_id == exercise.session_id
        ).order_by(Concentration.time.desc()).limit(1)
        
        conc_after_result = await self.db.execute(conc_after_stmt)
        concentration_after = conc_after_result.scalar()

        exercise.end_time = datetime.now()
        exercise.completed = True
        exercise.concentration_after = concentration_after

        await self.db.commit()

        effectiveness = self.utils.calculate_exercise_effectiveness(
            exercise.concentration_before, concentration_after
        )

        return {
            "success": True, 
            "message": "Упражнение завершено",
            "exercise_id": exercise_id,
            "concentration_before": exercise.concentration_before,
            "concentration_after": concentration_after,
            "effectiveness": effectiveness
        }

    async def skip_exercise(self, exercise_id: int):
        stmt = select(Exercise).where(Exercise.id == exercise_id)
        result = await self.db.execute(stmt)
        exercise = result.scalar_one()

        exercise.end_time = datetime.now()
        exercise.completed = False

        await self.db.commit()

        return {"success": True, "message": "Упражнение пропущено"}

    def get_available_exercises(self) -> List[Dict]:
        """Возвращает список доступных упражнений"""
        return [
            {
                "type": "breathing",
                "name": "Дыхательное упражнение",
                "description": "Глубокое дыхание для восстановления фокуса",
                "duration": 60,
                "instructions": [
                    "Сядьте удобно и закройте глаза",
                    "Сделайте глубокий вдох через нос на 4 секунды",
                    "Задержите дыхание на 7 секунды", 
                    "Медленно выдохните через рот на 8 секунд",
                    "Повторите 5-7 раз"
                ]
            },
            {
                "type": "physical", 
                "name": "Физическое упражнение",
                "description": "Легкая разминка для улучшения кровообращения",
                "duration": 90,
                "instructions": [
                    "Встаньте и потянитесь руками вверх",
                    "Сделайте 5-10 вращений плечами",
                    "Повращайте головой по кругу 3-5 раз",
                    "Сделайте 5-10 приседаний",
                    "Потянитесь в стороны"
                ]
            }
        ]

    async def get_session_exercises(self, session_id: int) -> List[Dict]:
        stmt = select(Exercise).where(
            Exercise.session_id == session_id
        ).order_by(Exercise.start_time.desc())
        
        result = await self.db.execute(stmt)
        exercises = result.scalars().all()
        
        return [
            {
                "exercise_id": ex.id,
                "type": ex.exercise_type,
                "start_time": ex.start_time,
                "end_time": ex.end_time,
                "completed": ex.completed,
                "concentration_before": ex.concentration_before,
                "concentration_after": ex.concentration_after
            }
            for ex in exercises
        ]

    async def get_exercise_effectiveness_stats(self, session_id: int) -> Dict[str, Any]:
        stmt = select(Exercise).where(
            Exercise.session_id == session_id,
            Exercise.completed == True,
            Exercise.concentration_before.isnot(None),
            Exercise.concentration_after.isnot(None)
        )
        
        result = await self.db.execute(stmt)
        exercises = result.scalars().all()
        
        if not exercises:
            return {
                "total_exercises": 0,
                "average_improvement": 0,
                "effectiveness_breakdown": {"high": 0, "medium": 0, "low": 0, "neutral": 0}
            }
        
        improvements = []
        effectiveness_count = {"high": 0, "medium": 0, "low": 0, "neutral": 0}
        
        for exercise in exercises:
            improvement = exercise.concentration_after - exercise.concentration_before
            improvements.append(improvement)
            
            effectiveness = self.utils.calculate_exercise_effectiveness(
                exercise.concentration_before, exercise.concentration_after
            )
            effectiveness_count[effectiveness] += 1
        
        return {
            "total_exercises": len(exercises),
            "average_improvement": round(sum(improvements) / len(improvements), 2),
            "max_improvement": round(max(improvements), 2),
            "min_improvement": round(min(improvements), 2),
            "effectiveness_breakdown": effectiveness_count
        }