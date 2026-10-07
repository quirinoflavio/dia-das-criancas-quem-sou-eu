"""Testes de votação, encerramento, pontuação e placar."""
from __future__ import annotations

import pytest

from app.domain.engine import (
    GameError,
    close_round,
    is_round_complete,
    maybe_autoclose_round,
    register_vote,
    round_vote_progress,
    score_round,
    scoreboard,
    start_game,
    winners,
)
from app.domain.enums import DisplayMode, Phase, RevealMode, RoundStatus
from tests.helpers import make_room, seeded_rng


def _start(n, **kw):
    room = make_room(n, **kw)
    start_game(room, rng=seeded_rng())
    return room


def test_self_vote_blocked():
    room = _start(4, k=1)
    target = room.current_round.targets[0]
    with pytest.raises(GameError) as e:
        register_vote(room, voter_id=target, target_id=target, guess_player_id="p1")
    assert e.value.code == "self_vote"


def test_vote_change_allowed_until_close():
    room = _start(4, k=1)
    rnd = room.current_round
    t = rnd.targets[0]
    voter = next(p for p in room.players if p != t)
    register_vote(room, voter, t, "p1")
    register_vote(room, voter, t, "p2")
    assert rnd.votes[t][voter] == "p2"


def test_progress_and_autoclose_single_target():
    room = _start(4, k=1)
    rnd = room.current_round
    t = rnd.targets[0]
    voters = [p for p in room.players if p != t]
    for i, v in enumerate(voters):
        register_vote(room, v, t, "p1")
        completed, total = round_vote_progress(room, rnd)
        assert total == 3
        assert completed == i + 1
    assert is_round_complete(room, rnd)
    assert maybe_autoclose_round(room) is True
    assert rnd.status == RoundStatus.CLOSED


def test_grouped_targets_require_vote_per_target():
    room = _start(6, k=3)
    rnd = room.current_round
    assert len(rnd.targets) == 3
    # cada votante elegível precisa votar em cada alvo em que não é alvo
    # Vote apenas em um alvo e verifique que não está completo.
    t0 = rnd.targets[0]
    voter = next(p for p in room.players if p not in rnd.targets)
    register_vote(room, voter, t0, "p0")
    completed, total = round_vote_progress(room, rnd)
    assert completed == 0  # ainda falta votar nos outros alvos


def test_force_close_with_pending_votes():
    room = _start(4, k=1)
    rnd = room.current_round
    with pytest.raises(GameError):
        close_round(room, forced=False)  # ninguém votou ainda
    close_round(room, forced=True)
    assert rnd.status == RoundStatus.CLOSED


def test_scoring_one_point_per_correct():
    room = _start(4, k=1)
    rnd = room.current_round
    t = rnd.targets[0]
    voters = [p for p in room.players if p != t]
    # dois acertam, um erra
    register_vote(room, voters[0], t, t)
    register_vote(room, voters[1], t, t)
    register_vote(room, voters[2], t, "p1" if "p1" != t else "p2")
    close_round(room, forced=True)
    score_round(room, rnd)
    assert room.players[voters[0]].score == 1
    assert room.players[voters[1]].score == 1
    # quem errou não pontua
    wrong = voters[2]
    assert room.players[wrong].score == 0


def test_scoreboard_ties_share_position():
    room = make_room(4, k=1)
    room.players["p0"].score = 2
    room.players["p1"].score = 2
    room.players["p2"].score = 1
    room.players["p3"].score = 0
    board = scoreboard(room)
    positions = {row["player_id"]: row["position"] for row in board}
    assert positions["p0"] == 1
    assert positions["p1"] == 1
    assert positions["p2"] == 3  # pula a posição 2 (empate acima)
    assert positions["p3"] == 4
    assert set(winners(room)) == {"p0", "p1"}
