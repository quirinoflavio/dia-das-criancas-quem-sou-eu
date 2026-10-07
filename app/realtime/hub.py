"""Hub de WebSocket: registra conexões por sala/jogador e faz broadcast."""
from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any

from fastapi import WebSocket


class Hub:
    def __init__(self) -> None:
        # room_code -> {player_id -> set[WebSocket]} (um jogador pode ter abas)
        self._conns: dict[str, dict[str, set[WebSocket]]] = defaultdict(
            lambda: defaultdict(set)
        )
        self._lock = asyncio.Lock()

    async def connect(self, room_code: str, player_id: str, ws: WebSocket) -> None:
        async with self._lock:
            self._conns[room_code][player_id].add(ws)

    async def disconnect(self, room_code: str, player_id: str, ws: WebSocket) -> bool:
        """Remove a conexão. Retorna True se o jogador ficou sem conexões."""
        async with self._lock:
            conns = self._conns.get(room_code, {}).get(player_id)
            if conns and ws in conns:
                conns.discard(ws)
            now_empty = not conns
            if now_empty and room_code in self._conns:
                self._conns[room_code].pop(player_id, None)
            return now_empty

    def player_ids(self, room_code: str) -> list[str]:
        return list(self._conns.get(room_code, {}).keys())

    async def send_to_player(
        self, room_code: str, player_id: str, message: dict[str, Any]
    ) -> None:
        for ws in list(self._conns.get(room_code, {}).get(player_id, set())):
            try:
                await ws.send_json(message)
            except Exception:  # noqa: BLE001 — conexão caiu; limpeza no disconnect
                pass

    async def broadcast_per_player(
        self, room_code: str, builder
    ) -> None:
        """Envia a cada jogador uma mensagem construída por `builder(player_id)`."""
        for pid in self.player_ids(room_code):
            message = builder(pid)
            if message is not None:
                await self.send_to_player(room_code, pid, message)
