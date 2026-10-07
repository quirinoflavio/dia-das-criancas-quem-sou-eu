// Lobby: lista de jogadores, upload de foto, config do host, iniciar.
import { useState } from "preact/hooks";
import { api } from "./api";
import { Badge, Panel } from "./components";
import type { DisplayMode, RevealMode, RoomState } from "./types";

const DISPLAY_LABELS: Record<DisplayMode, string> = {
  CHILD_ONLY: "Só foto de criança",
  GENERATED_ONLY: "Só foto gerada (hoje)",
  BOTH: "Ambas ao mesmo tempo",
  SEQ_CHILD_FIRST: "Uma por vez (criança 1º)",
  SEQ_GENERATED_FIRST: "Uma por vez (gerada 1º)",
  RANDOM: "Aleatório por rodada",
};

export function Lobby({ state }: { state: RoomState }) {
  const [error, setError] = useState<string | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const me = state.players.find((p) => p.id === state.you);
  const allPhotos = state.players.every((p) => p.has_photo);
  const needGen = ["GENERATED_ONLY", "BOTH", "SEQ_CHILD_FIRST", "SEQ_GENERATED_FIRST", "RANDOM"]
    .includes(state.config.display_mode);
  const genReady = state.players.every((p) => p.gen_status === "READY");
  const canStart = state.players.length >= 3 && allPhotos && (!needGen || genReady);

  const upload = async (file: File) => {
    setError(null);
    setPreview(URL.createObjectURL(file));
    try { await api.uploadPhoto(state.code, file); }
    catch (e) { setError((e as Error).message); }
  };

  const setConfig = (patch: Partial<typeof state.config>) =>
    api.updateConfig(state.code, { ...state.config, ...patch }).catch(
      (e) => setError((e as Error).message));

  return (
    <div class="wrap">
      <h1>SALA {state.code}</h1>
      <p class="muted">Compartilhe o link: <a href={`${location.origin}/?c=${state.code}`}>{location.origin}/?c={state.code}</a></p>

      <Panel>
        <h2>JOGADORES ({state.players.length})</h2>
        {state.players.map((p) => (
          <div key={p.id} style="display:flex;justify-content:space-between;padding:4px 0">
            <span>{p.nickname}{p.is_host ? " 👑" : ""}</span>
            <span>
              {p.has_photo ? "📷" : <span class="muted">sem foto</span>}{" "}
              {needGen && <Badge status={p.gen_status} />}
            </span>
          </div>
        ))}
      </Panel>

      <Panel>
        <h2>SUA FOTO DE CRIANÇA</h2>
        {preview && <img src={preview} style="max-width:160px;display:block;margin:8px 0" />}
        <input type="file" accept="image/jpeg,image/png,image/webp" capture="user"
          onChange={(e) => {
            const f = (e.target as HTMLInputElement).files?.[0];
            if (f) upload(f);
          }} />
        {me?.gen_status === "FAILED" && (
          <button class="btn" onClick={() => api.regen(state.code)}>TENTAR GERAR DE NOVO</button>
        )}
      </Panel>

      {state.is_host && (
        <Panel>
          <h2>CONFIGURAÇÃO (HOST)</h2>
          <label class="muted">Exibição da foto</label>
          <select value={state.config.display_mode}
            onChange={(e) => setConfig({ display_mode: (e.target as HTMLSelectElement).value as DisplayMode })}>
            {Object.entries(DISPLAY_LABELS).map(([k, v]) => <option value={k}>{v}</option>)}
          </select>
          <div style="height:0.5rem" />
          <label class="muted">Revelação</label>
          <select value={state.config.reveal_mode}
            onChange={(e) => setConfig({ reveal_mode: (e.target as HTMLSelectElement).value as RevealMode })}>
            <option value="END_OF_GAME">No fim de todas as rodadas</option>
            <option value="PER_ROUND">No fim de cada rodada</option>
          </select>
          <div style="height:0.5rem" />
          <label class="muted">Alvos por rodada</label>
          <select value={String(state.config.targets_per_round)}
            onChange={(e) => setConfig({ targets_per_round: Number((e.target as HTMLSelectElement).value) })}>
            <option value="1">1</option><option value="2">2</option><option value="3">3</option>
          </select>
          <div style="height:0.75rem" />
          <button class="btn ok" disabled={!canStart} onClick={() => api.start(state.code).catch((e) => setError((e as Error).message))}>
            INICIAR JOGO
          </button>
          {!canStart && <p class="muted" style="font-size:0.7rem">Precisa de 3+ jogadores, todas as fotos{needGen ? " e gerações prontas" : ""}.</p>}
        </Panel>
      )}
      {error && <p class="error">{error}</p>}
    </div>
  );
}
