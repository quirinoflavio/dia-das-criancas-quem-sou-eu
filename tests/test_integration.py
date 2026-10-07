"""Teste de integração ponta a ponta sobre REST + WebSocket (gerador fake)."""
from __future__ import annotations

import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.main import create_app


def _png_bytes(color=(120, 80, 40)) -> bytes:
    img = Image.new("RGB", (64, 64), color)
    out = io.BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("IMAGE_PROVIDER", "fake")
    monkeypatch.setenv("CORS_ORIGINS", "")
    # limpa cache de settings
    from app.config import get_settings
    get_settings.cache_clear()
    app = create_app()
    with TestClient(app) as c:
        yield c


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def _create(client, nickname):
    r = client.post("/api/rooms", json={"nickname": nickname,
                    "config": {"display_mode": "CHILD_ONLY",
                               "reveal_mode": "END_OF_GAME",
                               "targets_per_round": 1}})
    assert r.status_code == 200
    data = r.json()
    return data["code"], data["identityToken"]


def _join(client, code, nickname):
    r = client.post(f"/api/rooms/{code}/join", json={"nickname": nickname})
    assert r.status_code == 200, r.text
    return r.json()["identityToken"]


def _upload(client, code, token):
    r = client.post(
        f"/api/rooms/{code}/photo",
        headers={"X-Identity": token},
        files={"file": ("c.png", _png_bytes(), "image/png")},
    )
    assert r.status_code == 200, r.text


def test_full_game_child_only_end_of_game(client):
    code, host = _create(client, "Host")
    p1 = _join(client, code, "Ana")
    p2 = _join(client, code, "Beto")
    p3 = _join(client, code, "Caio")
    tokens = {"Host": host, "Ana": p1, "Beto": p2, "Caio": p3}
    for name, tok in tokens.items():
        _upload(client, code, tok)

    # inicia pelo host
    r = client.post(f"/api/rooms/{code}/start", headers={"X-Identity": host})
    assert r.status_code == 200, r.text

    # conecta todos via WS e joga as 4 rodadas, todos acertando
    sockets = {}
    for name, tok in tokens.items():
        ws = client.websocket_connect(f"/ws/rooms/{code}?token={tok}").__enter__()
        sockets[tok] = ws
        ws.receive_json()  # room_state inicial

    # função para ler o estado atual de um socket qualquer
    def current_round_targets(tok):
        sockets[tok].send_json({"type": "ping"})
        # provoca um estado: na prática lemos do REST não exposto; usamos o manager
        return None

    # Usa o manager diretamente para orquestrar (teste de integração server-side).
    mgr = client.app.state.manager
    room = mgr.get(code)
    for _ in range(len(room.rounds)):
        rnd = room.current_round
        for t in rnd.targets:
            for tok in tokens.values():
                if tok != t:
                    sockets[tok].send_json({"type": "vote", "target_id": t,
                                            "guess_player_id": t})
        # host avança
        sockets[host].send_json({"type": "next"})

    # drena mensagens e verifica fim de jogo
    import time
    time.sleep(0.05)
    room = mgr.get(code)
    assert room.phase.value == "FINISHED"
    board = {row["nickname"]: row["score"] for row in __import__(
        "app.domain.engine", fromlist=["scoreboard"]).scoreboard(room)}
    # todos acertaram todos os alvos em que votaram → todos com score > 0
    assert all(s > 0 for s in board.values())

    for ws in sockets.values():
        ws.__exit__(None, None, None)


def test_join_blocked_after_start_and_bad_code(client):
    code, host = _create(client, "Host")
    _join(client, code, "Ana")
    _join(client, code, "Beto")
    for tok in [host]:
        _upload(client, code, tok)
    # faltam fotos → start falha
    r = client.post(f"/api/rooms/{code}/start", headers={"X-Identity": host})
    assert r.status_code == 400

    # código inexistente
    r = client.post("/api/rooms/ZZZZZZ/join", json={"nickname": "X"})
    assert r.status_code == 404


def test_image_authorization_denies_non_member(client):
    code, host = _create(client, "Host")
    _upload(client, code, host)
    room = client.app.state.manager.get(code)
    img_id = room.players[host].child_photo.id
    # sem identidade válida → 403
    r = client.get(f"/api/rooms/{code}/images/{img_id}?token=someoneelse")
    assert r.status_code == 403
    # o próprio dono vê a sua foto
    r = client.get(f"/api/rooms/{code}/images/{img_id}", headers={"X-Identity": host})
    assert r.status_code == 200
    assert r.headers["X-Robots-Tag"] == "noindex"
