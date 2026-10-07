"""Task de limpeza periódica: remove salas inativas além do TTL."""
from __future__ import annotations

import asyncio

CLEANUP_INTERVAL_SECONDS = 600  # 10 min


async def cleanup_loop(manager) -> None:
    while True:
        try:
            await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)
            expired = [
                room for room in list(manager.rooms.values())
                if manager._expired(room)
            ]
            for room in expired:
                manager._destroy(room)
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 — nunca derruba o loop
            continue
