"""Modelos de domínio (Pydantic). Serializáveis para snapshot em disco."""
from __future__ import annotations

import secrets
from datetime import datetime, timezone

from pydantic import BaseModel, Field

from app.domain.enums import (
    DisplayMode,
    GenStatus,
    Phase,
    RevealMode,
    RoundStatus,
)

# Alfabeto sem caracteres ambíguos (sem 0/O, 1/I).
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 6

MIN_PLAYERS = 3
MAX_PLAYERS = 12


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def generate_code() -> str:
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))


class PhotoRef(BaseModel):
    id: str
    mime: str


class Player(BaseModel):
    id: str  # == identityToken; nunca exposto a outros clientes
    nickname: str
    is_host: bool = False
    child_photo: PhotoRef | None = None
    generated_photo: PhotoRef | None = None
    gen_status: GenStatus = GenStatus.NONE
    score: int = 0
    connected: bool = False

    @property
    def has_photo(self) -> bool:
        return self.child_photo is not None


class RoomConfig(BaseModel):
    display_mode: DisplayMode = DisplayMode.BOTH
    reveal_mode: RevealMode = RevealMode.END_OF_GAME
    targets_per_round: int = Field(default=1, ge=1, le=3)
    max_players: int = Field(default=MAX_PLAYERS, ge=MIN_PLAYERS, le=MAX_PLAYERS)


class Round(BaseModel):
    index: int
    targets: list[str]  # player_ids (1..3)
    # modo efetivo por alvo (resolve RANDOM na montagem)
    display_per_target: dict[str, DisplayMode]
    # para modos sequenciais: 0 = primeira imagem visível, 1 = segunda liberada
    seq_stage: dict[str, int] = Field(default_factory=dict)
    # target_id -> {voter_id -> guessed_player_id}
    votes: dict[str, dict[str, str]] = Field(default_factory=dict)
    status: RoundStatus = RoundStatus.VOTING


class Room(BaseModel):
    code: str
    phase: Phase = Phase.LOBBY
    host_id: str
    config: RoomConfig = Field(default_factory=RoomConfig)
    players: dict[str, Player] = Field(default_factory=dict)
    rounds: list[Round] = Field(default_factory=list)
    current_round_idx: int = 0
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)

    def touch(self) -> None:
        self.updated_at = now_utc()

    @property
    def player_order(self) -> list[Player]:
        return list(self.players.values())

    def nickname_taken(self, nickname: str) -> bool:
        norm = nickname.strip().casefold()
        return any(p.nickname.casefold() == norm for p in self.players.values())

    @property
    def current_round(self) -> Round | None:
        if 0 <= self.current_round_idx < len(self.rounds):
            return self.rounds[self.current_round_idx]
        return None
