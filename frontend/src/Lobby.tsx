// Lobby: lista de jogadores, upload de foto, config do host (modal), iniciar.
import { useState } from "preact/hooks";
import { api, imageUrl } from "./api";
import { Badge, ConfigModal, OptionGroup, Panel } from "./components";
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
  const [configOpen, setConfigOpen] = useState(false);
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
    <div class="wrap lobby">
      <header class="room-header">
        <h1>SALA {state.code}</h1>
        {state.is_host && (
          <button class="gear" aria-label="Configurações da sala" title="Configurações"
            onClick={() => setConfigOpen(true)}>⚙</button>
        )}
      </header>
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
        {(() => {
          const thumb = preview ?? (state.my_photo_url ? imageUrl(state.my_photo_url) : null);
          return (
            <div class="photo-upload">
              <div class={`photo-thumb${thumb ? "" : " empty"}`}>
                {thumb ? <img src={thumb} alt="Sua foto" /> : <span>SEM FOTO</span>}
              </div>
              <div class="photo-actions">
                {me?.has_photo && <p class="photo-ok">✓ Foto enviada</p>}
                <label class="btn secondary">
                  {me?.has_photo ? "TROCAR FOTO" : "ENVIAR FOTO"}
                  <input type="file" accept="image/jpeg,image/png,image/webp" capture="user"
                    style="display:none"
                    onChange={(e) => {
                      const f = (e.target as HTMLInputElement).files?.[0];
                      if (f) upload(f);
                    }} />
                </label>
                {me?.gen_status === "FAILED" && (
                  <button class="btn" onClick={() => api.regen(state.code)}>TENTAR GERAR DE NOVO</button>
                )}
              </div>
            </div>
          );
        })()}
      </Panel>

      {error && <p class="error">{error}</p>}

      {/* Botão de início: separado da config, fixo no rodapé e sempre visível (host). */}
      {state.is_host && (
        <div class="start-bar">
          {!canStart && (
            <p class="muted center" style="font-size:0.7rem;margin:0 0 0.5rem">
              Precisa de 3+ jogadores, todas as fotos{needGen ? " e gerações prontas" : ""}.
            </p>
          )}
          <button class="btn ok start-btn" disabled={!canStart}
            onClick={() => api.start(state.code).catch((e) => setError((e as Error).message))}>
            INICIAR JOGO
          </button>
        </div>
      )}

      {state.is_host && configOpen && (
        <ConfigModal title="CONFIGURAÇÃO (HOST)" onClose={() => setConfigOpen(false)}>
          <OptionGroup<DisplayMode>
            label="Exibição da foto"
            value={"CHILD_ONLY"}
            disabled
            note="Por enquanto só a foto de criança. Os modos com a foto gerada por IA chegam em breve."
            onChange={() => { /* bloqueado: geração desativada por ora */ }}
            options={(Object.keys(DISPLAY_LABELS) as DisplayMode[]).map((k) => ({ value: k, label: DISPLAY_LABELS[k] }))}
          />
          <OptionGroup<RevealMode>
            label="Revelação"
            value={state.config.reveal_mode}
            onChange={(v) => setConfig({ reveal_mode: v })}
            options={[
              { value: "END_OF_GAME", label: "No fim de todas as rodadas" },
              { value: "PER_ROUND", label: "No fim de cada rodada" },
            ]}
          />
          <OptionGroup<number>
            label="Alvos por rodada"
            compact
            value={state.config.targets_per_round}
            onChange={(v) => setConfig({ targets_per_round: v })}
            options={[
              { value: 1, label: "1" },
              { value: 2, label: "2" },
              { value: 3, label: "3" },
            ]}
          />
        </ConfigModal>
      )}
    </div>
  );
}
