"""Enums do domínio."""
from __future__ import annotations

from enum import Enum


class Phase(str, Enum):
    LOBBY = "LOBBY"
    GENERATING = "GENERATING"
    PLAYING = "PLAYING"
    REVEAL = "REVEAL"
    FINISHED = "FINISHED"


class DisplayMode(str, Enum):
    CHILD_ONLY = "CHILD_ONLY"
    GENERATED_ONLY = "GENERATED_ONLY"
    BOTH = "BOTH"
    SEQ_CHILD_FIRST = "SEQ_CHILD_FIRST"
    SEQ_GENERATED_FIRST = "SEQ_GENERATED_FIRST"
    RANDOM = "RANDOM"


class RevealMode(str, Enum):
    END_OF_GAME = "END_OF_GAME"
    PER_ROUND = "PER_ROUND"


class GenStatus(str, Enum):
    NONE = "NONE"
    PENDING = "PENDING"
    GENERATING = "GENERATING"
    READY = "READY"
    FAILED = "FAILED"


class RoundStatus(str, Enum):
    VOTING = "VOTING"
    CLOSED = "CLOSED"
    REVEALED = "REVEALED"


# Modos que exigem a foto gerada estar pronta antes do jogo começar.
MODES_REQUIRING_GENERATED = {
    DisplayMode.GENERATED_ONLY,
    DisplayMode.BOTH,
    DisplayMode.SEQ_CHILD_FIRST,
    DisplayMode.SEQ_GENERATED_FIRST,
    DisplayMode.RANDOM,  # pode sortear um modo que use a gerada
}

# Modos sequenciais (duas imagens, uma por vez).
SEQUENTIAL_MODES = {
    DisplayMode.SEQ_CHILD_FIRST,
    DisplayMode.SEQ_GENERATED_FIRST,
}

# Opções que o modo RANDOM pode sortear por alvo.
RANDOM_CHOICES = [
    DisplayMode.CHILD_ONLY,
    DisplayMode.GENERATED_ONLY,
    DisplayMode.BOTH,
]
