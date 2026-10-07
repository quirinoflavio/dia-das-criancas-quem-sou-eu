"""Helpers de teste para o domínio."""
from __future__ import annotations

import random

from app.domain.enums import DisplayMode, GenStatus, RevealMode
from app.domain.models import Player, PhotoRef, Room, RoomConfig


def make_room(n: int, *, display=DisplayMode.CHILD_ONLY,
              reveal=RevealMode.END_OF_GAME, k=1, with_photos=True,
              generated=False) -> Room:
    host_id = "p0"
    room = Room(
        code="ABC234",
        host_id=host_id,
        config=RoomConfig(display_mode=display, reveal_mode=reveal,
                          targets_per_round=k),
    )
    for i in range(n):
        pid = f"p{i}"
        player = Player(id=pid, nickname=f"Nick{i}", is_host=(i == 0))
        if with_photos:
            player.child_photo = PhotoRef(id=f"child-{pid}.jpg", mime="image/jpeg")
            if generated:
                player.generated_photo = PhotoRef(id=f"gen-{pid}.jpg", mime="image/jpeg")
                player.gen_status = GenStatus.READY
        room.players[pid] = player
    return room


def seeded_rng() -> random.Random:
    return random.Random(42)
