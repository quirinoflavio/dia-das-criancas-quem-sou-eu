"""Persistência leve: snapshot de salas em JSON e reload no start."""
from __future__ import annotations

from pathlib import Path

from app.domain.models import Room


class RoomStore:
    def __init__(self, rooms_path: Path):
        self._root = rooms_path

    def _path(self, code: str) -> Path:
        return self._root / f"{code}.json"

    def save(self, room: Room) -> None:
        self._path(room.code).write_text(
            room.model_dump_json(indent=0), encoding="utf-8"
        )

    def delete(self, code: str) -> None:
        p = self._path(code)
        if p.is_file():
            p.unlink()

    def load_all(self) -> list[Room]:
        rooms: list[Room] = []
        for f in self._root.glob("*.json"):
            try:
                rooms.append(Room.model_validate_json(f.read_text(encoding="utf-8")))
            except Exception:  # noqa: BLE001 — snapshot corrompido é ignorado
                continue
        return rooms
