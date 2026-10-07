"""RoomManager: cria/mantém salas, orquestra geração, persiste e notifica."""
from __future__ import annotations

import asyncio
from datetime import timedelta

from app.config import Settings
from app.domain.engine import GameError
from app.domain.enums import GenStatus, Phase
from app.domain.models import (
    MAX_PLAYERS,
    MIN_PLAYERS,
    PhotoRef,
    Player,
    Room,
    RoomConfig,
    generate_code,
    now_utc,
)
from app.domain.enums import DisplayMode, MODES_REQUIRING_GENERATED
from app.realtime.hub import Hub
from app.realtime.projection import project_room
from app.services.generation import ImageGenError, build_generator
from app.services.images import ImageStore
from app.services.persistence import RoomStore


class RoomManager:
    def __init__(self, settings: Settings, hub: Hub):
        self.settings = settings
        self.hub = hub
        self.rooms: dict[str, Room] = {}
        self.images = ImageStore(settings.images_path)
        self.store = RoomStore(settings.rooms_path)
        self.generator = build_generator(
            settings.image_provider, settings.image_api_key, settings.gemini_image_model
        )
        self._gen_tasks: set[asyncio.Task] = set()

    # ----------------------------------------------------------------- lifecycle
    def load_from_disk(self) -> None:
        for room in self.store.load_all():
            if not self._expired(room):
                self.rooms[room.code] = room

    def _expired(self, room: Room) -> bool:
        ttl = timedelta(hours=self.settings.room_ttl_hours)
        return now_utc() - room.updated_at > ttl

    def persist(self, room: Room) -> None:
        self.store.save(room)

    async def notify(self, room: Room) -> None:
        """Envia room_state projetado a todos os conectados."""
        await self.hub.broadcast_per_player(
            room.code, lambda pid: project_room(room, pid)
        )

    # -------------------------------------------------------------------- rooms
    def get(self, code: str) -> Room | None:
        return self.rooms.get(code.upper())

    def require(self, code: str) -> Room:
        room = self.get(code)
        if room is None:
            raise GameError("room_not_found", "Sala não encontrada ou encerrada.")
        return room

    def create_room(self, nickname: str, config: RoomConfig, identity: str) -> Room:
        nickname = nickname.strip()
        if not (1 <= len(nickname) <= 20):
            raise GameError("bad_nickname", "O apelido deve ter de 1 a 20 caracteres.")
        code = generate_code()
        while code in self.rooms:
            code = generate_code()
        room = Room(code=code, host_id=identity, config=config)
        room.players[identity] = Player(
            id=identity, nickname=nickname, is_host=True
        )
        self.rooms[code] = room
        self.persist(room)
        return room

    def join_room(self, code: str, nickname: str, identity: str) -> Room:
        room = self.require(code)
        nickname = nickname.strip()
        if not (1 <= len(nickname) <= 20):
            raise GameError("bad_nickname", "O apelido deve ter de 1 a 20 caracteres.")
        if identity in room.players:
            return room  # reentrada do mesmo jogador
        if room.phase != Phase.LOBBY:
            raise GameError("already_started", "O jogo já começou; não é possível entrar.")
        if len(room.players) >= room.config.max_players:
            raise GameError("room_full", "A sala está cheia.")
        if room.nickname_taken(nickname):
            raise GameError("nickname_taken", "Esse apelido já está em uso na sala.")
        room.players[identity] = Player(id=identity, nickname=nickname)
        room.touch()
        self.persist(room)
        return room

    def update_config(self, code: str, identity: str, config: RoomConfig) -> Room:
        room = self.require(code)
        self._require_host(room, identity)
        if room.phase != Phase.LOBBY:
            raise GameError("locked", "A configuração só pode mudar no lobby.")
        room.config = config
        room.touch()
        self.persist(room)
        return room

    def close_room(self, code: str, identity: str) -> None:
        room = self.require(code)
        self._require_host(room, identity)
        self._destroy(room)

    def _destroy(self, room: Room) -> None:
        self.images.delete_room(room.code)
        self.store.delete(room.code)
        self.rooms.pop(room.code, None)

    def _require_host(self, room: Room, identity: str) -> None:
        if room.host_id != identity:
            raise GameError("not_host", "Apenas o host pode fazer isso.")

    # ------------------------------------------------------------------- photos
    def set_photo(self, code: str, identity: str, raw: bytes, mime: str) -> Room:
        room = self.require(code)
        if identity not in room.players:
            raise GameError("not_member", "Você não está nesta sala.")
        if room.phase != Phase.LOBBY:
            raise GameError("locked", "As fotos só podem ser enviadas no lobby.")
        data, final_mime = self.images.normalize(raw, mime)
        image_id = self.images.save(room.code, data, final_mime)
        player = room.players[identity]
        player.child_photo = PhotoRef(id=image_id, mime=final_mime)
        player.generated_photo = None
        player.gen_status = GenStatus.NONE
        room.touch()
        self.persist(room)
        self._maybe_schedule_generation(room, identity)
        return room

    def _mode_needs_generation(self, room: Room) -> bool:
        return room.config.display_mode in MODES_REQUIRING_GENERATED

    def _maybe_schedule_generation(self, room: Room, identity: str) -> None:
        if not self._mode_needs_generation(room):
            return
        player = room.players[identity]
        if player.child_photo is None:
            return
        player.gen_status = GenStatus.PENDING
        task = asyncio.create_task(self._run_generation(room.code, identity))
        self._gen_tasks.add(task)
        task.add_done_callback(self._gen_tasks.discard)

    def regen_photo(self, code: str, identity: str, target_player: str) -> Room:
        room = self.require(code)
        # host ou o próprio dono podem pedir regen
        if identity != room.host_id and identity != target_player:
            raise GameError("not_allowed", "Sem permissão para regerar esta foto.")
        if target_player not in room.players:
            raise GameError("not_member", "Jogador não está na sala.")
        if room.players[target_player].child_photo is None:
            raise GameError("no_photo", "Não há foto de criança para regerar.")
        self._maybe_schedule_generation_for(room, target_player)
        return room

    def _maybe_schedule_generation_for(self, room: Room, target_player: str) -> None:
        room.players[target_player].gen_status = GenStatus.PENDING
        task = asyncio.create_task(self._run_generation(room.code, target_player))
        self._gen_tasks.add(task)
        task.add_done_callback(self._gen_tasks.discard)

    async def _run_generation(self, code: str, identity: str) -> None:
        room = self.get(code)
        if room is None or identity not in room.players:
            return
        player = room.players[identity]
        if player.child_photo is None:
            return
        player.gen_status = GenStatus.GENERATING
        await self.notify(room)
        try:
            raw = self.images.read(code, player.child_photo.id)
            if raw is None:
                raise ImageGenError("Foto de criança não encontrada.")
            result = await self.generator.generate_adult(raw, player.child_photo.mime)
            data, final_mime = self.images.normalize(result.data, result.mime)
            image_id = self.images.save(code, data, final_mime)
            player.generated_photo = PhotoRef(id=image_id, mime=final_mime)
            player.gen_status = GenStatus.READY
        except Exception as exc:  # noqa: BLE001
            player.gen_status = GenStatus.FAILED
            player.generated_photo = None
            await self.hub.send_to_player(
                code, identity, {"type": "error", "code": "gen_failed",
                                 "message": str(exc)}
            )
        room.touch()
        self.persist(room)
        await self.notify(room)
