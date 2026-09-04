import asyncio

from fastapi import WebSocket


class SimulationConnectionManager:
    """Keeps transport connections only; session state always lives in PostgreSQL."""

    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, simulation_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections.setdefault(simulation_id, set()).add(websocket)

    async def disconnect(self, simulation_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            connections = self._connections.get(simulation_id)
            if connections is None:
                return
            connections.discard(websocket)
            if not connections:
                self._connections.pop(simulation_id, None)
