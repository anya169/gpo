from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import asyncio
import json

from db import get_session
from services.session_service import SessionService
from services.concentration_service import ConcentrationService
from services.exercise_service import ExerciseService
from websocket_manager import manager

router = APIRouter()

class ConcentrationData(BaseModel):
    session_id: int
    value: float

class StartExerciseRequest(BaseModel):
    session_id: int
    exercise_type: str

class CompleteExerciseRequest(BaseModel):
    exercise_id: int

@router.post("/session/start")
async def start_session(
    user_id: int,
    db: AsyncSession = Depends(get_session)
):
    service = SessionService(db)
    result = await service.create_session(user_id)
    return result

@router.post("/session/end")
async def end_session(
    session_id: int,
    db: AsyncSession = Depends(get_session)
):
    service = SessionService(db)
    result = await service.end_session(session_id)
    return result

@router.get("/session/active")
async def get_active_session(
    user_id: int,
    db: AsyncSession = Depends(get_session)
):
    service = SessionService(db)
    return await service.get_active_session(user_id)

@router.post("/concentration/data")
async def add_concentration_data(
    data: ConcentrationData,
    db: AsyncSession = Depends(get_session)
):
    service = ConcentrationService(db)
    result = await service.add_concentration_data(data.session_id, data.value)
    
    #данные отправляются по вебсокету
    await manager.send_concentration_data(data.session_id, {
        "value": data.value,
        "timestamp": result["timestamp"].isoformat(),
        "detection_triggered": result["detection_triggered"]
    })
    
    if result["detection_triggered"]:
        exercise_service = ExerciseService(db)
        exercises = exercise_service.get_available_exercises()

        exercise_result = await exercise_service.start_exercise(data.session_id, "suggested")
        
        await manager.send_exercise_notification(data.session_id, {
            "type": "exercise_suggestion",
            "exercises": exercises,
            "current_concentration": result["current_value"],
            "exercise_id": exercise_result["exercise_id"]
        })
    
    return result

@router.post("/concentration/baseline")
async def set_baseline(
    session_id: int,
    baseline: float,
    db: AsyncSession = Depends(get_session)
):
    service = ConcentrationService(db)
    await service.set_baseline_concentration(session_id, baseline)

    await manager.broadcast_to_session(session_id, {
        "type": "baseline_set",
        "baseline": baseline
    })
    
    return {"success": True, "baseline_set": baseline}

@router.get("/concentration/history/{session_id}")
async def get_concentration_history(
    session_id: int,
    limit: int = 100,
    db: AsyncSession = Depends(get_session)
):
    service = ConcentrationService(db)
    return await service.get_concentration_history(session_id, limit)

@router.post("/exercise/start")
async def start_exercise(
    request: StartExerciseRequest,
    db: AsyncSession = Depends(get_session)
):
    service = ExerciseService(db)
    result = await service.start_exercise(request.session_id, request.exercise_type)
    
    await manager.send_exercise_notification(request.session_id, {
        "type": "exercise_started",
        "exercise_id": result["exercise_id"],
        "exercise_type": result["type"]
    })
    
    return result

@router.post("/exercise/complete")
async def complete_exercise(
    request: CompleteExerciseRequest,
    db: AsyncSession = Depends(get_session)
):
    service = ExerciseService(db)
    result = await service.complete_exercise(request.exercise_id)
    return result

@router.post("/exercise/skip")
async def skip_exercise(
    exercise_id: int,
    db: AsyncSession = Depends(get_session)
):
    service = ExerciseService(db)
    result = await service.skip_exercise(exercise_id)
    return result

@router.get("/exercises/available")
async def get_available_exercises():
    service = ExerciseService(None) 
    return service.get_available_exercises()

@router.get("/session/stats/{session_id}")
async def get_session_stats(
    session_id: int,
    db: AsyncSession = Depends(get_session)
):
    service = SessionService(db)
    return await service._calculate_session_stats(session_id)

@router.websocket("/ws/session/{session_id}")
async def websocket_session(websocket: WebSocket, session_id: int):
    await manager.connect(websocket, session_id)
    
    try:
        await manager.broadcast_to_session(session_id, {
            "type": "connection_established",
            "session_id": session_id,
            "message": "WebSocket подключен"
        })
        
        while True:
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                await handle_client_message(session_id, message)
            except json.JSONDecodeError:
                await manager.broadcast_to_session(session_id, {
                    "type": "error",
                    "message": "Неверный формат JSON",
                    "received_data": data
                })
                
    except WebSocketDisconnect:
        manager.disconnect(session_id)
        print(f"WebSocket отключен для сессии {session_id}")

async def handle_client_message(session_id: int, message: dict):
    message_type = message.get("type")
    
    if message_type == "start_exercise":
        exercise_type = message.get("exercise_type")
        if exercise_type:
            from db import get_session
            from services.exercise_service import ExerciseService
            
            async for db in get_session():
                service = ExerciseService(db)
                result = await service.start_exercise(session_id, exercise_type)
                
                await manager.send_exercise_notification(session_id, {
                    "type": "exercise_started",
                    "exercise_id": result["exercise_id"],
                    "exercise_type": result["type"]
                })
    
    elif message_type == "complete_exercise":
        exercise_id = message.get("exercise_id")
        if exercise_id:
            from db import get_session
            from services.exercise_service import ExerciseService
            
            async for db in get_session():
                service = ExerciseService(db)
                await service.complete_exercise(exercise_id)
                
                await manager.send_exercise_notification(session_id, {
                    "type": "exercise_completed",
                    "exercise_id": exercise_id
                })
    
    elif message_type == "skip_exercise":
        exercise_id = message.get("exercise_id")
        if exercise_id:
            from db import get_session
            from services.exercise_service import ExerciseService
            
            async for db in get_session():
                service = ExerciseService(db)
                await service.skip_exercise(exercise_id)
                
                await manager.send_exercise_notification(session_id, {
                    "type": "exercise_skipped",
                    "exercise_id": exercise_id
                })
    
    elif message_type == "get_history":
        limit = message.get("limit", 100)
        from db import get_session
        from services.concentration_service import ConcentrationService
        
        async for db in get_session():
            service = ConcentrationService(db)
            history = await service.get_concentration_history(session_id, limit)
            
            await manager.broadcast_to_session(session_id, {
                "type": "history_data",
                "data": history
            })

@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "active_sessions": len(manager.get_connected_sessions()),
        "connected_sessions": manager.get_connected_sessions()
    }