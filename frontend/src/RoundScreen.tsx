// Tela de rodada: mostra foto(s) do(s) alvo(s) e grade de votação.
import { Hud, PixelFrame } from "./components";
import type { RoomState } from "./types";

export function RoundScreen({ state, send }: {
  state: RoomState; send: (m: object) => void;
}) {
  const rnd = state.round;
  if (!rnd) return <div class="wrap">Carregando rodada…</div>;
  const others = state.players; // votamos escolhendo entre todos
  const isHost = state.is_host;

  return (
    <div class="wrap">
      <Hud round={rnd.index} total={state.num_rounds} votes={rnd.vote_progress} />
      {rnd.targets.map((t) => {
        const amITarget = t.target_id === state.you;
        const myVote = rnd.my_votes[t.target_id] ?? null;
        return (
          <div key={t.target_id} class="panel">
            <h2>QUEM É?</h2>
            <div class="center">
              {t.child && <PixelFrame src={t.child} label="CRIANÇA" fit="cover" />}
              {t.generated && <PixelFrame src={t.generated} label="HOJE" fit="cover" />}
              {!t.child && !t.generated && <p class="muted">Aguardando imagem…</p>}
            </div>
            {isHost && t.seq_stage === 0 && (
              <button class="btn secondary" onClick={() => send({ type: "advance_image", target_id: t.target_id })}>
                MOSTRAR 2ª IMAGEM
              </button>
            )}
            {amITarget ? (
              <p class="muted center">Essa é você — aguarde os votos.</p>
            ) : (
              <div class="vote-grid">
                {others.filter((p) => p.id !== state.you).map((p) => (
                  <button key={p.id}
                    class={`btn ${myVote === p.id ? "chosen" : ""}`}
                    onClick={() => send({ type: "vote", target_id: t.target_id, guess_player_id: p.id })}>
                    {p.nickname}
                  </button>
                ))}
              </div>
            )}
          </div>
        );
      })}
      {isHost && (
        <button class="btn" onClick={() => send({ type: "force_close_round" })}>
          ENCERRAR VOTAÇÃO AGORA
        </button>
      )}
    </div>
  );
}
