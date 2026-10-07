"""Projeção do estado da sala por destinatário (privacidade — §8 / RNF-1).

Regra central: o servidor nunca envia a um cliente dados que ele ainda não pode
ver. Imagens de alvos só aparecem conforme a fase e o display_mode; identidades
reais e o mapa de votos só na revelação.
"""
from __future__ import annotations

from typing import Any

from app.domain.engine import round_vote_progress, scoreboard, winners
from app.domain.enums import DisplayMode, Phase, RoundStatus
from app.domain.models import Room, Round


def _image_url(room_code: str, image_id: str) -> str:
    return f"/api/rooms/{room_code}/images/{image_id}"


def _public_player(room: Room, pid: str) -> dict[str, Any]:
    p = room.players[pid]
    return {
        "id": pid,  # usado como chave de voto; não é o identityToken? -> é.
        "nickname": p.nickname,
        "is_host": p.is_host,
        "connected": p.connected,
        "has_photo": p.has_photo,
        "gen_status": p.gen_status.value,
        "score": p.score,
    }


def _lobby_players(room: Room) -> list[dict[str, Any]]:
    # No lobby ninguém vê a foto de ninguém; só status.
    return [_public_player(room, pid) for pid in room.players]


def _target_images(room: Room, rnd: Round, target_id: str) -> dict[str, Any]:
    """Imagens liberadas para o alvo conforme o modo e o estágio sequencial."""
    p = room.players[target_id]
    mode = rnd.display_per_target[target_id]
    child = (
        _image_url(room.code, p.child_photo.id) if p.child_photo else None
    )
    generated = (
        _image_url(room.code, p.generated_photo.id) if p.generated_photo else None
    )
    show_child = False
    show_generated = False

    if mode == DisplayMode.CHILD_ONLY:
        show_child = True
    elif mode == DisplayMode.GENERATED_ONLY:
        show_generated = True
    elif mode == DisplayMode.BOTH:
        show_child = show_generated = True
    elif mode == DisplayMode.SEQ_CHILD_FIRST:
        show_child = True
        show_generated = rnd.seq_stage.get(target_id, 0) >= 1
    elif mode == DisplayMode.SEQ_GENERATED_FIRST:
        show_generated = True
        show_child = rnd.seq_stage.get(target_id, 0) >= 1

    return {
        "target_id": target_id,
        "mode": mode.value,
        "seq_stage": rnd.seq_stage.get(target_id),
        "child": child if show_child else None,
        "generated": generated if show_generated else None,
    }


def _reveal_payload(room: Room, rnd: Round) -> dict[str, Any]:
    """Identidade real + fotos completas + mapa de votos (só na revelação)."""
    targets = []
    for tid in rnd.targets:
        p = room.players[tid]
        votes = [
            {"voter_id": vid, "voter_nickname": room.players[vid].nickname,
             "guess_id": guess, "guess_nickname": room.players[guess].nickname,
             "correct": guess == tid}
            for vid, guess in rnd.votes.get(tid, {}).items()
            if vid in room.players and guess in room.players
        ]
        targets.append(
            {
                "target_id": tid,
                "nickname": p.nickname,
                "child": _image_url(room.code, p.child_photo.id) if p.child_photo else None,
                "generated": _image_url(room.code, p.generated_photo.id)
                if p.generated_photo
                else None,
                "votes": votes,
            }
        )
    return {"round_index": rnd.index, "targets": targets}


def project_room(room: Room, viewer_id: str) -> dict[str, Any]:
    """Estado completo projetado para `viewer_id`."""
    base: dict[str, Any] = {
        "type": "room_state",
        "code": room.code,
        "phase": room.phase.value,
        "you": viewer_id,
        "is_host": room.players.get(viewer_id).is_host if viewer_id in room.players else False,
        "config": {
            "display_mode": room.config.display_mode.value,
            "reveal_mode": room.config.reveal_mode.value,
            "targets_per_round": room.config.targets_per_round,
            "max_players": room.config.max_players,
        },
        "players": _lobby_players(room),
        "num_rounds": len(room.rounds),
        "current_round_idx": room.current_round_idx,
    }

    if room.phase in (Phase.LOBBY, Phase.GENERATING):
        return base

    rnd = room.current_round
    if room.phase == Phase.PLAYING and rnd is not None:
        completed, total = round_vote_progress(room, rnd)
        # imagens apenas dos alvos da rodada atual, no estágio permitido
        base["round"] = {
            "index": rnd.index,
            "status": rnd.status.value,
            "targets": [_target_images(room, rnd, t) for t in rnd.targets],
            "vote_progress": {"completed": completed, "total": total},
            # o próprio voto do viewer (para ele reabrir e ver sua escolha)
            "my_votes": {
                t: rnd.votes.get(t, {}).get(viewer_id)
                for t in rnd.targets
                if t != viewer_id
            },
        }
        return base

    if room.phase == Phase.REVEAL and rnd is not None:
        base["reveal"] = _reveal_payload(room, rnd)
        base["scoreboard"] = scoreboard(room)
        return base

    if room.phase == Phase.FINISHED:
        base["reveals"] = [
            _reveal_payload(room, r)
            for r in room.rounds
            if r.status == RoundStatus.REVEALED
        ]
        base["scoreboard"] = scoreboard(room)
        base["winners"] = winners(room)
        return base

    return base
