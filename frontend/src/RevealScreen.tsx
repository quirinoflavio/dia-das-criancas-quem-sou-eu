// Telas de revelação (por rodada) e final (placar arcade + galeria).
import { RevealGallery, PixelFrame, Scoreboard } from "./components";
import type { RevealTarget, RoomState } from "./types";

function RevealBlock({ t }: { t: RevealTarget }) {
  return (
    <div class="panel">
      <h2>ERA… {t.nickname}!</h2>
      <div class="center">
        {t.child && <PixelFrame src={t.child} label="CRIANÇA" />}
        {t.generated && <PixelFrame src={t.generated} label="HOJE" />}
      </div>
      <div style="margin-top:0.5rem">
        {t.votes.map((v) => (
          <div key={v.voter_id} style="display:flex;justify-content:space-between">
            <span>{v.voter_nickname} → {v.guess_nickname}</span>
            <span>{v.correct ? "✅" : "❌"}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export function RevealScreen({ state, send }: {
  state: RoomState; send: (m: object) => void;
}) {
  const targets = state.reveal?.targets ?? [];
  return (
    <div class="wrap">
      <h1>REVELAÇÃO</h1>
      {targets.map((t) => <RevealBlock t={t} key={t.target_id} />)}
      {state.scoreboard && <Scoreboard rows={state.scoreboard} />}
      {state.is_host && (
        <button class="btn ok" onClick={() => send({ type: "next" })}>CONTINUAR</button>
      )}
    </div>
  );
}

export function FinishedScreen({ state, send, onLeave }: {
  state: RoomState; send: (m: object) => void; onLeave: () => void;
}) {
  const reveals = state.reveals ?? [];
  const allTargets = reveals.flatMap((r) => r.targets);
  return (
    <div class="wrap gameover">
      <div class="crt-scanlines" aria-hidden="true" />

      <h1 class="center gameover-title">
        <span class="go-word">GAME</span> <span class="go-word go-word-2">OVER</span>
      </h1>

      {state.scoreboard && (
        <Scoreboard rows={state.scoreboard} winners={state.winners} reveals={allTargets} />
      )}

      <p class="insert-coin muted display center" style="font-size:0.55rem;margin:1rem 0 0.5rem">
        <span class="coin" aria-hidden="true"><span class="coin-face">★</span></span>
        INSERT COIN TO CONTINUE
      </p>

      <h2 class="center" style="margin-top:1rem">REVELAÇÕES</h2>
      <RevealGallery targets={allTargets} />

      <div class="start-bar gameover-actions">
        {state.is_host ? (
          <button class="btn ok start-btn press-start" onClick={() => send({ type: "play_again" })}>
            VOLTAR AO SALÃO
          </button>
        ) : (
          <p class="muted center blink" style="margin:0 0 0.5rem">Aguardando o host voltar ao salão…</p>
        )}
        <button class="btn secondary start-btn" onClick={onLeave}>SAIR</button>
      </div>
    </div>
  );
}
