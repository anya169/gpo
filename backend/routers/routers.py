from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any
from datetime import datetime, date, timedelta
import calendar
from collections import defaultdict

from db import get_session
from services.service import StatisticsService
from dependencies import get_current_user

router = APIRouter()

@router.get("/dashboard/summary")
async def get_dashboard_summary(
    db: AsyncSession = Depends(get_session),
    current_user: Dict = Depends(get_current_user)
):
    """Сводная статистика для личного кабинета (сегодня + неделя)"""
    service = StatisticsService(db)
    user_id = current_user["user_id"]
    
    today_stats = await service.get_today_stats(user_id)
    week_stats = await service.get_current_week_stats(user_id)
    
    session_history = await service.get_session_history(user_id, limit=10)
    
    return {
        "today": today_stats,
        "week": week_stats,
        "recent_sessions": session_history,
        "user_id": user_id
    }

@router.get("/statistics/daily/{target_date}")
async def get_daily_statistics(
    target_date: str,
    db: AsyncSession = Depends(get_session),
    current_user: Dict = Depends(get_current_user)
):
    """Подробная статистика за конкретный день"""
    try:
        target = date.fromisoformat(target_date)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный формат даты. Используйте формат YYYY-MM-DD"
        )
    
    service = StatisticsService(db)
    user_id = current_user["user_id"]
    
    stats = await service.get_daily_statistics(user_id, target)
    
    prev_day = target - timedelta(days=1)
    next_day = target + timedelta(days=1)
    
    return {
        **stats,
        "navigation": {
            "prev_day": prev_day.isoformat(),
            "next_day": next_day.isoformat(),
            "current_day": date.today().isoformat(),
            "target_day": target.isoformat()
        }
    }

@router.get("/statistics/weekly/{week_start}")
async def get_weekly_statistics(
    week_start: str,
    db: AsyncSession = Depends(get_session),
    current_user: Dict = Depends(get_current_user)
):
    """Подробная статистика за конкретную неделю"""
    try:
        week_start_date = date.fromisoformat(week_start)
        if week_start_date.weekday() != 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Дата начала недели должна быть понедельником"
            )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный формат даты. Используйте формат YYYY-MM-DD"
        )
    
    service = StatisticsService(db)
    user_id = current_user["user_id"]
    
    stats = await service.get_weekly_statistics(user_id, week_start_date)
    
    prev_week = week_start_date - timedelta(weeks=1)
    next_week = week_start_date + timedelta(weeks=1)
    current_week_start = date.today() - timedelta(days=date.today().weekday())
    
    return {
        **stats,
        "navigation": {
            "prev_week": prev_week.isoformat(),
            "next_week": next_week.isoformat(),
            "current_week": current_week_start.isoformat(),
            "target_week": week_start_date.isoformat()
        }
    }

@router.get("/sessions/history")
async def get_session_history(
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_session),
    current_user: Dict = Depends(get_current_user)
):
    """История сессий пользователя"""
    service = StatisticsService(db)
    user_id = current_user["user_id"]
    
    return await service.get_session_history(user_id, limit, offset)

@router.get("/sessions/{session_id}/detailed")
async def get_session_detailed(
    session_id: int,
    db: AsyncSession = Depends(get_session),
    current_user: Dict = Depends(get_current_user)
):
    """Подробная статистика конкретной сессии"""
    service = StatisticsService(db)
    user_id = current_user["user_id"]
    
    session_details = await service.get_session_detailed(user_id, session_id)
    
    if not session_details:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Сессия не найдена"
        )
    
    prev_session, next_session = await service.get_adjacent_sessions(user_id, session_id)
    
    return {
        **session_details,
        "navigation": {
            "prev_session_id": prev_session,
            "next_session_id": next_session,
            "current_session_id": session_id
        }
    }

@router.get("/statistics/range")
async def get_statistics_range(
    start_date: str,
    end_date: str,
    db: AsyncSession = Depends(get_session),
    current_user: Dict = Depends(get_current_user)
):
    """Статистика за произвольный период"""
    try:
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
        
        if start > end:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Дата начала не может быть позже даты окончания"
            )
            
        if (end - start).days > 365:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Период не может превышать 365 дней"
            )
            
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный формат даты. Используйте формат YYYY-MM-DD"
        )
    
    service = StatisticsService(db)
    user_id = current_user["user_id"]
    
    return await service.get_statistics_range(user_id, start, end)