// Componentes de tema 8-bit reutilizáveis.
import type { ComponentChildren } from "preact";
import { imageUrl } from "./api";
import type { ScoreRow } from "./types";

export function Panel({ children }: { children: ComponentChildren }) {
  return <div class="panel">{children}</div>;
}

export function PixelFrame({ src, label }: { src: string; label?: string }) {
  return (
    <div class="pixel-frame">
      <img src={imageUrl(src)} alt={label ?? "foto"} />
      {label && <div class="label">{label}</div>}
    </div>
  );
}

export function Hud({ round, total, votes }: {
  round?: number; total?: number; votes?: { completed: number; total: number };
}) {
  return (
    <div class="hud">
      <span>{round != null && total != null ? `ROUND ${round + 1}-${total}` : ""}</span>
      <span>{votes ? `VOTES ${votes.completed}/${votes.total}` : ""}</span>
    </div>
  );
}

export function Scoreboard({ rows, winners }: { rows: ScoreRow[]; winners?: string[] }) {
  const cls = (pos: number) =>
    pos === 1 ? "row gold" : pos === 2 ? "row silver" : pos === 3 ? "row bronze" : "row";
  return (
    <div class="scoreboard panel">
      <h2>HIGH SCORE</h2>
      {rows.map((r) => (
        <div class={cls(r.position)} key={r.player_id}>
          <span class={winners?.includes(r.player_id) ? "blink" : ""}>
            {r.position}. {r.nickname}
          </span>
          <span>{r.score}</span>
        </div>
      ))}
    </div>
  );
}

export function Badge({ status }: { status: string }) {
  const map: Record<string, string> = {
    READY: "ready", FAILED: "failed", PENDING: "pending", GENERATING: "pending",
  };
  const cls = map[status];
  if (!cls) return null;
  const label = { READY: "OK", FAILED: "ERRO", PENDING: "...", GENERATING: "GER" }[status];
  return <span class={`badge ${cls}`}>{label}</span>;
}
