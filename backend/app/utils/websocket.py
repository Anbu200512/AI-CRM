import json
import logging
from typing import Dict, List
from fastapi import WebSocket

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        # Maps user_id -> list of WebSockets
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        logger.info(f"User {user_id} connected via WebSocket. Total connections for user: {len(self.active_connections[user_id])}")

    def disconnect(self, websocket: WebSocket, user_id: int):
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        logger.info(f"User {user_id} disconnected from WebSocket.")

    async def broadcast_to_user(self, user_id: int, message: dict):
        """Send a JSON message to all active WebSocket connections for a specific user."""
        if user_id in self.active_connections:
            # Create a copy to iterate to avoid runtime errors if connections drop
            connections = list(self.active_connections[user_id])
            for connection in connections:
                try:
                    await connection.send_text(json.dumps(message))
                except Exception as e:
                    logger.error(f"Error sending message to user {user_id} on websocket: {e}")

    def broadcast_sync(self, user_id: int, message: dict):
        """Helper to broadcast synchronously from worker threads."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(self.broadcast_to_user(user_id, message))
            else:
                loop.run_until_complete(self.broadcast_to_user(user_id, message))
        except Exception:
            asyncio.run(self.broadcast_to_user(user_id, message))

manager = ConnectionManager()
