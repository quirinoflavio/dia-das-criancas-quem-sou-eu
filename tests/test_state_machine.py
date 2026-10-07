"""Testes da máquina de estados e fluxo de revelação."""
from __future__ import annotations

import pytest

from app.domain.engine import (
    GameError,
    advance,
    register_vote,
    reset_to_lobby,
    score_round,
    start_game,
)
from app.domain.enums import Phase, RevealMode, RoundStatus
from tests.helpers import make_room, seeded_rng


def _start(n, **kw):
    room = make_room(n, **kw)
    start_game(room, rng=seeded_rng())
    return room


def _vote_all_correct(room):
    rnd = room.current_round
    for t in rnd.targets:
        for voter in room.players:
            if voter != t:
                register_vote(room, voter, t, t)


def test_end_of_game_plays_all_then_finishes():
    room = _start(4, k=1, reveal=RevealMode.END_OF_GAME)
    for _ in range(len(room.rounds)):
        _vote_all_correct(room)
        advance(room)  # host 'next' em END_OF_GAME avança a rodada
    assert room.phase == Phase.FINISHED
    # todos acertaram todos → cada um pontua (n_rounds - rodadas em que foi alvo)
    assert all(r.status == RoundStatus.REVEALED for r in room.rounds)


def test_per_round_alternates_reveal_and_play():
    room = _start(3, k=1, reveal=RevealMode.PER_ROUND)
    # rodada 0
    _vote_all_correct(room)
    advance(room)  # fecha+pontua+REVEAL
    assert room.phase == Phase.REVEAL
    assert room.current_round.status == RoundStatus.REVEALED
    advance(room)  # volta a jogar rodada 1
    assert room.phase == Phase.PLAYING
    assert room.current_round_idx == 1
    # joga até o fim
    _vote_all_correct(room)
    advance(room)
    assert room.phase == Phase.REVEAL
    advance(room)
    _vote_all_correct(room)
    advance(room)
    assert room.phase == Phase.REVEAL
    advance(room)
    assert room.phase == Phase.FINISHED


def test_no_double_scoring_when_autoclosed_then_advanced():
    room = _start(3, k=1, reveal=RevealMode.END_OF_GAME)
    rnd = room.current_round
    t = rnd.targets[0]
    voters = [p for p in room.players if p != t]
    for v in voters:
        register_vote(room, v, t, t)
    # simula o caminho do WS: já fechou e pontuou, depois host 'next'
    from app.domain.engine import maybe_autoclose_round
    maybe_autoclose_round(room)
    score_round(room, rnd)
    first_scores = {p: room.players[p].score for p in room.players}
    advance(room)  # não deve pontuar de novo a mesma rodada
    for v in voters:
        assert room.players[v].score == first_scores[v]


def test_reset_to_lobby_reuses_room_and_resets_scores():
    room = _start(3, k=1, reveal=RevealMode.END_OF_GAME, generated=True)
    # joga o jogo inteiro com todos acertando -> acumula placar
    for _ in range(len(room.rounds)):
        _vote_all_correct(room)
        advance(room)
    assert room.phase == Phase.FINISHED
    assert any(p.score > 0 for p in room.players.values())

    photos_before = {
        pid: (p.child_photo.id, p.generated_photo.id)
        for pid, p in room.players.items()
    }
    players_before = set(room.players.keys())

    reset_to_lobby(room)

    assert room.phase == Phase.LOBBY
    assert room.rounds == []
    assert room.current_round_idx == 0
    assert all(p.score == 0 for p in room.players.values())
    # jogadores e fotos (criança + gerada) preservados — opção A
    assert set(room.players.keys()) == players_before
    for pid, p in room.players.items():
        assert (p.child_photo.id, p.generated_photo.id) == photos_before[pid]

    # a sala pode jogar de novo normalmente
    start_game(room, rng=seeded_rng())
    assert room.phase == Phase.PLAYING


def test_reset_to_lobby_rejected_before_finished():
    room = _start(3, k=1)
    assert room.phase == Phase.PLAYING
    with pytest.raises(GameError):
        reset_to_lobby(room)
