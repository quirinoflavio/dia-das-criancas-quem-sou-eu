// Componentes de tema 8-bit reutilizáveis.
import type { ComponentChildren } from "preact";
import { useEffect } from "preact/hooks";
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

/* Modal de configuração — overlay com backdrop, fecha no X, backdrop ou Esc.
   Mantém a tela principal do lobby limpa (config fora do fluxo). */
export function ConfigModal({ title, onClose, children }: {
  title: string; onClose: () => void; children: ComponentChildren;
}) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);
  return (
    <div class="modal-backdrop" onClick={onClose}>
      <div class="modal-box" role="dialog" aria-modal="true" aria-label={title}
        onClick={(e: MouseEvent) => e.stopPropagation()}>
        <div class="modal-head">
          <h2>{title}</h2>
          <button class="modal-close" aria-label="Fechar" onClick={onClose}>✕</button>
        </div>
        <div class="modal-body">{children}</div>
      </div>
    </div>
  );
}

/* Grupo de opções estilo arcade (segmented radio) — substitui <select>.
   Acessível: role=radiogroup, aria-checked, navegável por teclado. */
export function OptionGroup<T extends string | number>({
  label, value, options, onChange, compact,
}: {
  label: string;
  value: T;
  options: { value: T; label: string }[];
  onChange: (v: T) => void;
  compact?: boolean;
}) {
  return (
    <div class={`optgroup${compact ? " compact" : ""}`}>
      <span class="optlabel">{label}</span>
      <div class="options" role="radiogroup" aria-label={label}>
        {options.map((o) => {
          const selected = o.value === value;
          return (
            <div
              key={String(o.value)}
              class={`opt${selected ? " selected" : ""}`}
              role="radio"
              aria-checked={selected}
              tabIndex={selected ? 0 : -1}
              onClick={() => onChange(o.value)}
              onKeyDown={(e: KeyboardEvent) => {
                if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onChange(o.value); }
              }}
            >
              {o.label}
            </div>
          );
        })}
      </div>
    </div>
  );
}
