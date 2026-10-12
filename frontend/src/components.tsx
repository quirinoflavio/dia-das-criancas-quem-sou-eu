// Componentes de tema 8-bit reutilizáveis.
import type { ComponentChildren } from "preact";
import { useEffect, useRef, useState } from "preact/hooks";
import { imageUrl } from "./api";
import type { RevealTarget, ScoreRow } from "./types";

export function Panel({ children }: { children: ComponentChildren }) {
  return <div class="panel">{children}</div>;
}

export function PixelFrame({ src, label, fit = "contain" }: {
  src: string; label?: string; fit?: "cover" | "contain";
}) {
  return (
    <div class={`pixel-frame fit-${fit}`}>
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

export function Scoreboard({ rows, winners, reveals }: {
  rows: ScoreRow[]; winners?: string[]; reveals?: RevealTarget[];
}) {
  const medal = (pos: number) => (pos === 1 ? "🥇" : pos === 2 ? "🥈" : pos === 3 ? "🥉" : "");
  const rankLabel = (pos: number) =>
    pos === 1 ? "1ST" : pos === 2 ? "2ND" : pos === 3 ? "3RD" : `${pos}TH`;
  const cls = (pos: number) =>
    pos === 1 ? "row gold" : pos === 2 ? "row silver" : pos === 3 ? "row bronze" : "row";

  // Acertos por jogador: quantas vezes votou certo ao longo de todas as revelações.
  const hitsByPlayer: Record<string, { hits: number; total: number }> = {};
  if (reveals) {
    for (const t of reveals) {
      for (const v of t.votes) {
        const e = (hitsByPlayer[v.voter_id] ??= { hits: 0, total: 0 });
        e.total += 1;
        if (v.correct) e.hits += 1;
      }
    }
  }
  const showHits = reveals != null && reveals.length > 0;

  return (
    <div class="scoreboard panel arcade">
      <div class="hiscore-head">
        <span class="blink">HIGH SCORE</span>
      </div>
      <div class={`sb-row sb-header${showHits ? " with-hits" : ""}`}>
        <span>RANK</span>
        <span>NAME</span>
        {showHits && <span class="num">HITS</span>}
        <span class="num">SCORE</span>
      </div>
      {rows.map((r) => {
        const h = hitsByPlayer[r.player_id];
        const isWinner = winners?.includes(r.player_id);
        return (
          <div class={`sb-row ${cls(r.position)}${showHits ? " with-hits" : ""}${isWinner ? " champ" : ""}`} key={r.player_id}>
            <span class="rank">{medal(r.position)}<em>{rankLabel(r.position)}</em></span>
            <span class={`pname${isWinner ? " blink" : ""}`}>{r.nickname}</span>
            {showHits && <span class="num">{h ? `${h.hits}/${h.total}` : "—"}</span>}
            <span class="num score">{String(r.score).padStart(2, "0")}</span>
          </div>
        );
      })}
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

/* Galeria navegável de revelações: uma por vez, setas + swipe + teclado. */
export function RevealGallery({ targets }: { targets: RevealTarget[] }) {
  const [i, setI] = useState(0);
  const touchX = useRef<number | null>(null);
  const n = targets.length;
  const go = (d: number) => setI((cur) => (cur + d + n) % n);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "ArrowLeft") go(-1);
      if (e.key === "ArrowRight") go(1);
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [n]);

  if (n === 0) return null;
  const t = targets[i];
  const hits = t.votes.filter((v) => v.correct).length;

  return (
    <div class="gallery panel">
      <div class="gallery-nav">
        <button class="btn secondary nav" aria-label="Anterior" disabled={n < 2} onClick={() => go(-1)}>‹</button>
        <span class="gallery-count display">{i + 1}/{n}</span>
        <button class="btn secondary nav" aria-label="Próxima" disabled={n < 2} onClick={() => go(1)}>›</button>
      </div>
      <div
        class="gallery-slide"
        onTouchStart={(e: TouchEvent) => { touchX.current = e.touches[0].clientX; }}
        onTouchEnd={(e: TouchEvent) => {
          if (touchX.current == null) return;
          const dx = e.changedTouches[0].clientX - touchX.current;
          if (Math.abs(dx) > 40) go(dx < 0 ? 1 : -1);
          touchX.current = null;
        }}
      >
        <h2>ERA… {t.nickname}!</h2>
        <div class="center gallery-photos">
          {t.child && <PixelFrame src={t.child} label="CRIANÇA" />}
          {t.generated && <PixelFrame src={t.generated} label="HOJE" />}
        </div>
        <p class="muted center" style="font-size:0.7rem">{hits}/{t.votes.length} acertaram</p>
        <div class="gallery-votes">
          {t.votes.map((v) => (
            <div key={v.voter_id} class="vote-row">
              <span>{v.voter_nickname} → {v.guess_nickname}</span>
              <span>{v.correct ? "✅" : "❌"}</span>
            </div>
          ))}
        </div>
      </div>
      {n > 1 && (
        <div class="gallery-dots" aria-hidden="true">
          {targets.map((_, k) => <span key={k} class={`dot${k === i ? " on" : ""}`} />)}
        </div>
      )}
    </div>
  );
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
  label, value, options, onChange, compact, disabled, note,
}: {
  label: string;
  value: T;
  options: { value: T; label: string }[];
  onChange: (v: T) => void;
  compact?: boolean;
  disabled?: boolean;
  note?: string;
}) {
  return (
    <div class={`optgroup${compact ? " compact" : ""}${disabled ? " disabled" : ""}`}>
      <span class="optlabel">{label}</span>
      <div class="options" role="radiogroup" aria-label={label} aria-disabled={disabled}>
        {options.map((o) => {
          const selected = o.value === value;
          return (
            <div
              key={String(o.value)}
              class={`opt${selected ? " selected" : ""}`}
              role="radio"
              aria-checked={selected}
              aria-disabled={disabled}
              tabIndex={disabled ? -1 : selected ? 0 : -1}
              onClick={() => { if (!disabled) onChange(o.value); }}
              onKeyDown={(e: KeyboardEvent) => {
                if (disabled) return;
                if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onChange(o.value); }
              }}
            >
              {o.label}
            </div>
          );
        })}
      </div>
      {note && <span class="optnote">{note}</span>}
    </div>
  );
}
