"""Rota WebSocket: conexão por sala + handlers de eventos de jogo."""
from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.domain.engine import (
    GameError,
    advance,
    advance_sequential_image,
    close_round,
    maybe_autoclose_round,
    register_vote,
    score_round,
)
from app.domain.enums import Phase, RevealMode
from app.realtime.projection import project_room

router = APIRouter()


@router.websocket("/ws/rooms/{code}")
async def room_ws(ws: WebSocket, code: str, token: str = ""):
    mgr = ws.app.state.manager
    room = mgr.get(code)
    if room is None or token not in room.players:
        await ws.close(code=4404)
        return

    await ws.accept()
    await mgr.hub.connect(code, token, ws)
    room.players[token].connected = True
    await ws.send_json(project_room(room, token))
    await mgr.notify(room)

    try:
        while True:
            msg = await ws.receive_json()
            await _handle(mgr, room.code, token, msg, ws)
    except WebSocketDisconnect:
        pass
    finally:
        now_empty = await mgr.hub.disconnect(code, token, ws)
        current = mgr.get(code)
        if current and now_empty and token in current.players:
            current.players[token].connected = False
            await mgr.notify(current)


async def _handle(mgr, code: str, token: str, msg: dict, ws: WebSocket) -> None:
    room = mgr.get(code)
    if room is None:
        return
    mtype = msg.get("type")
    try:
        if mtype == "ping":
            await ws.send_json({"type": "pong"})
            return

        if mtype == "vote":
            register_vote(room, token, msg["target_id"], msg["guess_player_id"])
            closed = maybe_autoclose_round(room)
            if closed and room.config.reveal_mode == RevealMode.PER_ROUND:
                # revela automaticamente quando todos votam, no modo por rodada
                score_round(room, room.current_round)
                room.phase = Phase.REVEAL
            elif closed and room.config.reveal_mode == RevealMode.END_OF_GAME:
                score_round(room, room.current_round)
                advance(room)  # segue para a próxima rodada
            mgr.persist(room)
            await mgr.notify(room)
            return

        # A partir daqui, só o host.
        if room.host_id != token:
            await ws.send_json({"type": "error", "code": "not_host",
                                "message": "Apenas o host pode fazer isso."})
            return

        if mtype == "advance_image":
            advance_sequential_image(room, msg["target_id"])
        elif mtype == "force_close_round":
            close_round(room, forced=True)
            if room.config.reveal_mode == RevealMode.PER_ROUND:
                score_round(room, room.current_round)
                room.phase = Phase.REVEAL
            else:
                score_round(room, room.current_round)
                advance(room)
        elif mtype == "next":
            advance(room)
        else:
            await ws.send_json({"type": "error", "code": "bad_type",
                                "message": f"Tipo desconhecido: {mtype}"})
            return

        mgr.persist(room)
        await mgr.notify(room)

    except GameError as e:
        await ws.send_json({"type": "error", "code": e.code, "message": e.message})
    except KeyError as e:
        await ws.send_json({"type": "error", "code": "bad_payload",
                            "message": f"Campo ausente: {e}"})
