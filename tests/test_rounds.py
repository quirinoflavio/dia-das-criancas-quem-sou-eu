"""Testes de montagem de rodadas e pré-condições de início."""
from __future__ import annotations

import random

import pytest

from app.domain.engine import GameError, build_rounds, check_can_start, start_game
from app.domain.enums import DisplayMode, GenStatus, Phase, RANDOM_CHOICES
from app.domain.models import generate_code, CODE_ALPHABET, CODE_LENGTH
from tests.helpers import make_room, seeded_rng


def test_code_generation_unambiguous_and_length():
    for _ in range(200):
        code = generate_code()
        assert len(code) == CODE_LENGTH
        assert all(c in CODE_ALPHABET for c in code)
        assert not set(code) & set("01OI")


def test_rounds_k3_seven_players():
    room = make_room(7, k=3)
    rounds = build_rounds(room, rng=seeded_rng())
    sizes = [len(r.targets) for r in rounds]
    assert sizes == [3, 3, 1]
    # todos os jogadores aparecem exatamente uma vez como alvo
    all_targets = [t for r in rounds for t in r.targets]
    assert sorted(all_targets) == sorted(room.players.keys())


def test_rounds_k1():
    room = make_room(5, k=1)
    rounds = build_rounds(room, rng=seeded_rng())
    assert len(rounds) == 5
    assert all(len(r.targets) == 1 for r in rounds)


def test_random_mode_resolves_per_target_within_choices():
    room = make_room(6, display=DisplayMode.RANDOM, k=2, generated=True)
    rounds = build_rounds(room, rng=random.Random(1))
    for r in rounds:
        for tid, mode in r.display_per_target.items():
            assert mode in RANDOM_CHOICES


def test_order_is_shuffled_not_insertion_order():
    room = make_room(8, k=1)
    rounds = build_rounds(room, rng=random.Random(7))
    order = [r.targets[0] for r in rounds]
    insertion = list(room.players.keys())
    assert order != insertion  # extremamente improvável coincidir com seed fixa


def test_start_requires_min_players():
    room = make_room(2)
    with pytest.raises(GameError) as e:
        check_can_start(room)
    assert e.value.code == "too_few"


def test_start_blocked_when_photo_missing():
    room = make_room(3, with_photos=False)
    with pytest.raises(GameError) as e:
        check_can_start(room)
    assert e.value.code == "photos_pending"


def test_start_blocked_when_generation_pending():
    room = make_room(3, display=DisplayMode.BOTH, generated=False)
    # tem fotos de criança mas não geradas
    for p in room.players.values():
        p.gen_status = GenStatus.PENDING
    with pytest.raises(GameError) as e:
        check_can_start(room)
    assert e.value.code == "generation_pending"


def test_start_ok_child_only():
    room = make_room(4, display=DisplayMode.CHILD_ONLY)
    start_game(room, rng=seeded_rng())
    assert room.phase == Phase.PLAYING
    assert len(room.rounds) == 4
