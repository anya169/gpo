from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio

from db import get_session
from service.neiry_service import NeiryHeadbendService
from service.calibration_service import CalibrationService
from websocket_manager import manager

router = APIRouter()

neiry_service = NeiryHeadbendService()
calibration_services = {}

class ConnectNeiryRequest(BaseModel):
    device_name: str = "Neiry Headbend"

@router.post("/neiry/connect")
async def connect_neiry(
    request: ConnectNeiryRequest,
    db: AsyncSession = Depends(get_session)
):
    success = await neiry_service.connect(request.device_name)
    return {"connected": success}

@router.post("/neiry/disconnect")
async def disconnect_neiry():
    await neiry_service.disconnect()
    return {"connected": False}

@router.post("/calibration/start/{session_id}")
async def start_calibration(
    session_id: int,
    duration: int = 120,
    db: AsyncSession = Depends(get_session)
):
    calibration_service = CalibrationService(db, neiry_service)
    calibration_services[session_id] = calibration_service
    
    calibration_service.add_progress_callback(
        lambda progress: manager.send_calibration_progress(session_id, progress)
    )
    
    result = await calibration_service.start_calibration(session_id, duration)
    return result

@router.post("/calibration/complete/{session_id}")
async def complete_calibration(
    session_id: int,
    db: AsyncSession = Depends(get_session)
):
    if session_id not in calibration_services:
        return {"success": False, "error": "Калибровка не запущена для этой сессии"}
    
    calibration_service = calibration_services[session_id]
    result = await calibration_service.complete_calibration(session_id)

    del calibration_services[session_id]
    
    return result

@router.get("/calibration/progress/{session_id}")
async def get_calibration_progress(session_id: int):
    if session_id not in calibration_services:
        return {"is_active": False}
    
    calibration_service = calibration_services[session_id]
    return await calibration_service.get_calibration_progress(session_id)

@router.websocket("/ws/calibration/{session_id}")
async def websocket_calibration(websocket: WebSocket, session_id: int):
    await manager.connect(websocket, session_id)
    
    try:
        while True:
            if session_id in calibration_services:
                progress = await calibration_services[session_id].get_calibration_progress(session_id)
                await manager.send_calibration_progress(session_id, progress)
            await asyncio.sleep(1)
            
    except WebSocketDisconnect:
        manager.disconnect(session_id)