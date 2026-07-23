from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from core.websocket import manager

router = APIRouter(tags=["WebSockets"])

@router.websocket("/ws/incidents")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # The connection stays open here, listening for client-side disconnects
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)