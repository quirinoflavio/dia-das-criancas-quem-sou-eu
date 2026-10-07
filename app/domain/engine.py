"""GameEngine: regras puras do jogo (montagem de rodadas, votação, pontuação,
máquina de estados). Sem I/O; opera sobre modelos de domínio."""
from __future__ import annotations

import random

from app.domain.enums import (
    MODES_REQUIRING_GENERATED,
    RANDOM_CHOICES,
    SEQUENTIAL_MODES,
    DisplayMode,
    GenStatus,
    Phase,
    RevealMode,
    RoundStatus,
)
from app.domain.models import (
    MAX_PLAYERS,
    MIN_PLAYERS,
    Player,
    Room,
    Round,
)


class GameError(Exception):
    """Erro de regra de jogo (vira 4xx / evento de erro)."""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


# --------------------------------------------------------------------------- #
# Pré-condições e montagem (B2, B5)
# --------------------------------------------------------------------------- #
def requires_generated(mode: DisplayMode) -> bool:
    return mode in MODES_REQUIRING_GENERATED


def check_can_start(room: Room) -> None:
    """Levanta GameError se o jogo não pode iniciar."""
    if room.phase != Phase.LOBBY:
        raise GameError("bad_phase", "O jogo só pode iniciar a partir do lobby.")
    n = len(room.players)
    if n < MIN_PLAYERS:
        raise GameError("too_few", f"São necessários ao menos {MIN_PLAYERS} jogadores.")
    if n > MAX_PLAYERS:
        raise GameError("too_many", f"Máximo de {MAX_PLAYERS} jogadores.")
    missing_photo = [p.nickname for p in room.players.values() if not p.has_photo]
    if missing_photo:
        raise GameError("photos_pending", "Há jogadores sem foto enviada.")
    if requires_generated(room.config.display_mode):
        not_ready = [
            p.nickname
            for p in room.players.values()
            if p.gen_status != GenStatus.READY
        ]
        if not_ready:
            raise GameError(
                "generation_pending",
                "As fotos geradas ainda não estão prontas para todos.",
            )


def _resolve_display(mode: DisplayMode, rng: random.Random) -> DisplayMode:
    if mode == DisplayMode.RANDOM:
        return rng.choice(RANDOM_CHOICES)
    return mode


def build_rounds(room: Room, rng: random.Random | None = None) -> list[Round]:
    """Embaralha jogadores e particiona em rodadas de `targets_per_round`."""
    rng = rng or random.Random()
    ids = list(room.players.keys())
    rng.shuffle(ids)
    k = room.config.targets_per_round
    rounds: list[Round] = []
    for i in range(0, len(ids), k):
        group = ids[i : i + k]
        display_per_target: dict[str, DisplayMode] = {}
        seq_stage: dict[str, int] = {}
        for tid in group:
            resolved = _resolve_display(room.config.display_mode, rng)
            display_per_target[tid] = resolved
            if resolved in SEQUENTIAL_MODES:
                seq_stage[tid] = 0
        rounds.append(
            Round(
                index=len(rounds),
                targets=group,
                display_per_target=display_per_target,
                seq_stage=seq_stage,
            )
        )
    return rounds


def start_game(room: Room, rng: random.Random | None = None) -> None:
    check_can_start(room)
    room.rounds = build_rounds(room, rng=rng)
    room.current_round_idx = 0
    room.phase = Phase.PLAYING
    room.touch()


# --------------------------------------------------------------------------- #
# Votação e encerramento (B3)
# --------------------------------------------------------------------------- #
def eligible_voters(room: Room, target_id: str) -> list[str]:
    """Todos os jogadores exceto o próprio alvo podem votar nesse alvo."""
    return [pid for pid in room.players if pid != target_id]


def register_vote(
    room: Room, voter_id: str, target_id: str, guess_player_id: str
) -> None:
    rnd = room.current_round
    if room.phase != Phase.PLAYING or rnd is None or rnd.status != RoundStatus.VOTING:
        raise GameError("not_voting", "A votação não está aberta.")
    if target_id not in rnd.targets:
        raise GameError("bad_target", "Esse alvo não pertence à rodada atual.")
    if voter_id == target_id:
        raise GameError("self_vote", "Você não vota sobre si mesmo como alvo.")
    if voter_id not in room.players:
        raise GameError("not_member", "Votante não está na sala.")
    if guess_player_id not in room.players:
        raise GameError("bad_guess", "Palpite inválido.")
    rnd.votes.setdefault(target_id, {})[voter_id] = guess_player_id


def round_vote_progress(room: Room, rnd: Round) -> tuple[int, int]:
    """(votantes que completaram todos os alvos, total de votantes elegíveis).

    Um votante é elegível se existe ao menos um alvo em que ele não é o alvo.
    Ele "completou" quando votou em todos os alvos para os quais é elegível.
    """
    everyone = list(room.players.keys())
    completed = 0
    eligible_total = 0
    for pid in everyone:
        targets_for_pid = [t for t in rnd.targets if t != pid]
        if not targets_for_pid:
            continue  # jogador é o único alvo e não vota em ninguém nesta rodada
        eligible_total += 1
        if all(pid in rnd.votes.get(t, {}) for t in targets_for_pid):
            completed += 1
    return completed, eligible_total


def is_round_complete(room: Room, rnd: Round) -> bool:
    completed, total = round_vote_progress(room, rnd)
    return total > 0 and completed == total


def close_round(room: Room, forced: bool = False) -> None:
    rnd = room.current_round
    if rnd is None or rnd.status != RoundStatus.VOTING:
        raise GameError("not_voting", "Não há rodada em votação.")
    if not forced and not is_round_complete(room, rnd):
        raise GameError("votes_pending", "Ainda há votos pendentes.")
    rnd.status = RoundStatus.CLOSED
    room.touch()


def maybe_autoclose_round(room: Room) -> bool:
    """Fecha a rodada automaticamente se todos votaram. Retorna True se fechou."""
    rnd = room.current_round
    if rnd is None or rnd.status != RoundStatus.VOTING:
        return False
    if is_round_complete(room, rnd):
        rnd.status = RoundStatus.CLOSED
        room.touch()
        return True
    return False


def advance_sequential_image(room: Room, target_id: str) -> None:
    rnd = room.current_round
    if rnd is None or rnd.status != RoundStatus.VOTING:
        raise GameError("not_voting", "A rodada não está em votação.")
    if target_id not in rnd.seq_stage:
        raise GameError("not_sequential", "Esse alvo não está em modo sequencial.")
    rnd.seq_stage[target_id] = 1
    room.touch()


# --------------------------------------------------------------------------- #
# Pontuação e placar (B4)
# --------------------------------------------------------------------------- #
def score_round(room: Room, rnd: Round) -> None:
    """Aplica +1 por acerto para cada alvo da rodada. Idempotente por rodada:
    só pontua rodadas CLOSED que ainda não foram REVEALED."""
    if rnd.status != RoundStatus.CLOSED:
        return
    for target_id in rnd.targets:
        for voter_id, guess in rnd.votes.get(target_id, {}).items():
            if guess == target_id and voter_id in room.players:
                room.players[voter_id].score += 1
    rnd.status = RoundStatus.REVEALED
    room.touch()


def scoreboard(room: Room) -> list[dict]:
    """Ranking ordenado desc por score, com posição compartilhada em empate."""
    players = sorted(
        room.players.values(), key=lambda p: p.score, reverse=True
    )
    result: list[dict] = []
    last_score: int | None = None
    position = 0
    for i, p in enumerate(players):
        if p.score != last_score:
            position = i + 1
            last_score = p.score
        result.append(
            {"player_id": p.id, "nickname": p.nickname, "score": p.score, "position": position}
        )
    return result


def winners(room: Room) -> list[str]:
    if not room.players:
        return []
    top = max(p.score for p in room.players.values())
    return [p.id for p in room.players.values() if p.score == top]


# --------------------------------------------------------------------------- #
# Avanço de fase: revelar / próxima rodada / finalizar (B5)
# --------------------------------------------------------------------------- #
def advance(room: Room) -> None:
    """Avança o jogo: fecha->revela a rodada, segue para a próxima ou finaliza,
    respeitando reveal_mode. Chamado pelo host via 'next'."""
    if room.phase not in (Phase.PLAYING, Phase.REVEAL):
        raise GameError("bad_phase", "Nada a avançar nesta fase.")

    rnd = room.current_round

    if room.phase == Phase.PLAYING:
        if rnd is None:
            raise GameError("no_round", "Sem rodada atual.")
        if rnd.status == RoundStatus.VOTING:
            # força encerramento ao avançar
            rnd.status = RoundStatus.CLOSED
        if room.config.reveal_mode == RevealMode.PER_ROUND:
            score_round(room, rnd)
            room.phase = Phase.REVEAL
            room.touch()
            return
        # END_OF_GAME: pontua silenciosamente e segue jogando
        score_round(room, rnd)
        _goto_next_round_or_reveal(room)
        return

    # phase == REVEAL (PER_ROUND): volta a jogar a próxima ou finaliza
    _goto_next_round_or_reveal(room)


def _goto_next_round_or_reveal(room: Room) -> None:
    if room.current_round_idx + 1 < len(room.rounds):
        room.current_round_idx += 1
        room.phase = Phase.PLAYING
    else:
        # acabaram as rodadas (todas já pontuadas/reveladas durante o jogo)
        room.phase = Phase.FINISHED
    room.touch()
