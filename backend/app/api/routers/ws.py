from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException
from app.utils.websocket import manager
from jose import JWTError, jwt
from app.config.settings import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ws", tags=["WebSockets"])

@router.websocket("/dashboard")
async def websocket_dashboard(websocket: WebSocket, token: str = Query(...)):
    user_id = None
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        sub = payload.get("sub")
        if sub is None:
            await websocket.close(code=1008)
            return
        user_id = int(sub)
    except JWTError as e:
        logger.warning(f"WebSocket auth failed: {e}")
        await websocket.close(code=1008)
        return

    await manager.connect(websocket, user_id)
    try:
        while True:
            # We don't expect the client to send much data, but we need to keep the connection alive
            # and detect when they disconnect.
            data = await websocket.receive_text()
            # Could handle ping/pong here if needed
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
        manager.disconnect(websocket, user_id)
