// Telas de revelação (por rodada) e final (placar + jogar de novo).
import { PixelFrame, Scoreboard } from "./components";
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
  return (
    <div class="wrap">
      <h1>GAME OVER</h1>
      {state.scoreboard && <Scoreboard rows={state.scoreboard} winners={state.winners} />}
      <details>
        <summary class="display" style="font-size:0.7rem;cursor:pointer">VER TODAS AS REVELAÇÕES</summary>
        {reveals.flatMap((r) => r.targets).map((t) => <RevealBlock t={t} key={t.target_id} />)}
      </details>
      {state.is_host ? (
        <button class="btn ok" onClick={() => send({ type: "play_again" })}>VOLTAR AO SALÃO</button>
      ) : (
        <p class="muted center blink">Aguardando o host voltar ao salão…</p>
      )}
      <button class="btn secondary" onClick={onLeave}>SAIR</button>
    </div>
  );
}
