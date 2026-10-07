"""Rotas REST: criar/entrar/configurar sala, upload/serve de imagem, iniciar/encerrar."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Header, HTTPException, Request, Response, UploadFile
from fastapi import File, Form
from pydantic import BaseModel

from app.domain.engine import GameError, start_game
from app.domain.enums import Phase, RoundStatus
from app.domain.models import RoomConfig
from app.realtime.projection import project_room
from app.services.images import ImageError
from app.services.room_manager import RoomManager

router = APIRouter(prefix="/api")


def _manager(request: Request) -> RoomManager:
    return request.app.state.manager


def _identity(x_identity: str | None) -> str:
    return x_identity or uuid.uuid4().hex


def _game_error_status(code: str) -> int:
    return {
        "room_not_found": 404,
        "nickname_taken": 409,
        "already_started": 423,
        "room_full": 403,
        "not_host": 403,
        "not_member": 403,
        "not_allowed": 403,
        "locked": 409,
    }.get(code, 400)


class CreateRoomBody(BaseModel):
    nickname: str
    config: RoomConfig = RoomConfig()


class JoinBody(BaseModel):
    nickname: str


class ConfigBody(BaseModel):
    config: RoomConfig


@router.post("/rooms")
async def create_room(body: CreateRoomBody, request: Request,
                      x_identity: str | None = Header(default=None)):
    identity = _identity(x_identity)
    mgr = _manager(request)
    client_ip = request.client.host if request.client else "unknown"
    if not request.app.state.rl_create.allow(client_ip):
        raise HTTPException(429, "Muitas salas criadas. Tente novamente em instantes.")
    try:
        room = mgr.create_room(body.nickname, body.config, identity)
    except GameError as e:
        raise HTTPException(_game_error_status(e.code), e.message)
    return {"code": room.code, "identityToken": identity,
            "room": project_room(room, identity)}


@router.post("/rooms/{code}/join")
async def join_room(code: str, body: JoinBody, request: Request,
                    x_identity: str | None = Header(default=None)):
    identity = _identity(x_identity)
    mgr = _manager(request)
    try:
        room = mgr.join_room(code, body.nickname, identity)
    except GameError as e:
        raise HTTPException(_game_error_status(e.code), e.message)
    await mgr.notify(room)
    return {"code": room.code, "identityToken": identity,
            "room": project_room(room, identity)}


@router.patch("/rooms/{code}/config")
async def update_config(code: str, body: ConfigBody, request: Request,
                        x_identity: str | None = Header(default=None)):
    mgr = _manager(request)
    try:
        room = mgr.update_config(code, x_identity or "", body.config)
    except GameError as e:
        raise HTTPException(_game_error_status(e.code), e.message)
    await mgr.notify(room)
    return {"room": project_room(room, x_identity or "")}


@router.post("/rooms/{code}/photo")
async def upload_photo(code: str, request: Request,
                       file: UploadFile = File(...),
                       x_identity: str | None = Header(default=None)):
    mgr = _manager(request)
    settings = request.app.state.settings
    rl_key = (x_identity or "") + ":" + (request.client.host if request.client else "?")
    if not request.app.state.rl_upload.allow(rl_key):
        raise HTTPException(429, "Muitos envios. Aguarde um momento.")
    raw = await file.read()
    if len(raw) > settings.max_upload_bytes:
        raise HTTPException(413, "Imagem maior que o limite permitido.")
    try:
        room = mgr.set_photo(code, x_identity or "", raw, file.content_type or "")
    except ImageError as e:
        raise HTTPException(400, e.message)
    except GameError as e:
        raise HTTPException(_game_error_status(e.code), e.message)
    await mgr.notify(room)
    return {"ok": True}


class RegenBody(BaseModel):
    player_id: str | None = None


@router.post("/rooms/{code}/photo/regen")
async def regen_photo(code: str, body: RegenBody, request: Request,
                      x_identity: str | None = Header(default=None)):
    mgr = _manager(request)
    target = body.player_id or (x_identity or "")
    try:
        mgr.regen_photo(code, x_identity or "", target)
    except GameError as e:
        raise HTTPException(_game_error_status(e.code), e.message)
    return {"ok": True}


@router.get("/rooms/{code}/images/{image_id}")
async def serve_image(code: str, image_id: str, request: Request,
                      x_identity: str | None = Header(default=None)):
    mgr = _manager(request)
    room = mgr.get(code)
    if room is None:
        raise HTTPException(404, "Sala não encontrada.")
    identity = x_identity or request.query_params.get("token", "")
    if identity not in room.players:
        raise HTTPException(403, "Acesso negado.")
    if not _can_view_image(room, identity, image_id):
        raise HTTPException(403, "Imagem não liberada.")
    data = mgr.images.read(code, image_id)
    if data is None:
        raise HTTPException(404, "Imagem não encontrada.")
    mime = "image/jpeg" if image_id.endswith(("jpg", "jpeg")) else (
        "image/png" if image_id.endswith("png") else "image/webp")
    return Response(content=data, media_type=mime, headers={
        "Cache-Control": "private, max-age=60",
        "X-Robots-Tag": "noindex",
    })


def _can_view_image(room, identity: str, image_id: str) -> bool:
    """Uma imagem só é servível quando o estado de jogo a libera para o viewer."""
    # Localiza o dono e se é child/generated.
    owner = None
    kind = None
    for p in room.players.values():
        if p.child_photo and p.child_photo.id == image_id:
            owner, kind = p, "child"
            break
        if p.generated_photo and p.generated_photo.id == image_id:
            owner, kind = p, "generated"
            break
    if owner is None:
        return False
    # O próprio dono pode ver a sua foto a qualquer momento.
    if owner.id == identity:
        return True
    if room.phase in (Phase.LOBBY, Phase.GENERATING):
        return False  # ninguém vê foto de outro no lobby
    if room.phase == Phase.FINISHED:
        return True  # tudo revelado
    rnd = room.current_round
    if rnd is None:
        return False
    if owner.id not in rnd.targets:
        # Em REVEAL mostramos a rodada atual; fora dela, nega.
        return room.phase == Phase.REVEAL and owner.id in rnd.targets
    if room.phase == Phase.REVEAL:
        return True
    # PLAYING: libera conforme display/seq
    from app.domain.enums import DisplayMode
    mode = rnd.display_per_target.get(owner.id)
    stage = rnd.seq_stage.get(owner.id, 0)
    if mode == DisplayMode.CHILD_ONLY:
        return kind == "child"
    if mode == DisplayMode.GENERATED_ONLY:
        return kind == "generated"
    if mode == DisplayMode.BOTH:
        return True
    if mode == DisplayMode.SEQ_CHILD_FIRST:
        return kind == "child" or (kind == "generated" and stage >= 1)
    if mode == DisplayMode.SEQ_GENERATED_FIRST:
        return kind == "generated" or (kind == "child" and stage >= 1)
    return False


@router.post("/rooms/{code}/start")
async def start(code: str, request: Request,
                x_identity: str | None = Header(default=None)):
    mgr = _manager(request)
    try:
        room = mgr.require(code)
        mgr._require_host(room, x_identity or "")
        start_game(room)
        mgr.persist(room)
    except GameError as e:
        raise HTTPException(_game_error_status(e.code), e.message)
    await mgr.notify(room)
    return {"ok": True}


@router.post("/rooms/{code}/close")
async def close(code: str, request: Request,
                x_identity: str | None = Header(default=None)):
    mgr = _manager(request)
    try:
        mgr.close_room(code, x_identity or "")
    except GameError as e:
        raise HTTPException(_game_error_status(e.code), e.message)
    return {"ok": True}
