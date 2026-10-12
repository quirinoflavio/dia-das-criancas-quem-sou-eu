// Tela inicial: criar sala ou entrar por código.
import { useState } from "preact/hooks";
import { api } from "./api";
import { Panel } from "./components";
import type { RoomConfig } from "./types";

const DEFAULT_CONFIG: RoomConfig = {
  display_mode: "BOTH",
  reveal_mode: "END_OF_GAME",
  targets_per_round: 1,
  max_players: 12,
};

export function Home({ onEnter, initialCode }: {
  onEnter: (code: string) => void; initialCode?: string;
}) {
  const [nickname, setNickname] = useState("");
  const [code, setCode] = useState(initialCode ?? "");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const create = async () => {
    setBusy(true); setError(null);
    try {
      const r = await api.createRoom(nickname.trim(), DEFAULT_CONFIG);
      onEnter(r.code);
    } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  };

  const join = async () => {
    setBusy(true); setError(null);
    try {
      await api.joinRoom(code.trim().toUpperCase(), nickname.trim());
      onEnter(code.trim().toUpperCase());
    } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  };

  return (
    <div class="wrap center">
      <h1>QUEM SOU EU?</h1>
      <p class="insert-coin muted display" style="font-size:0.6rem">
        <span class="coin" aria-hidden="true"><span class="coin-face">★</span></span>
        INSERT COIN · DIA DAS CRIANÇAS
      </p>
      <Panel>
        <input
          placeholder="SEU APELIDO"
          maxLength={20}
          value={nickname}
          onInput={(e) => setNickname((e.target as HTMLInputElement).value)}
        />
        <div style="height:0.75rem" />
        <button class="btn ok" disabled={busy || !nickname.trim()} onClick={create}>
          CRIAR SALA
        </button>
      </Panel>
      <Panel>
        <input
          placeholder="CÓDIGO DA SALA"
          maxLength={6}
          value={code}
          onInput={(e) => setCode((e.target as HTMLInputElement).value.toUpperCase())}
        />
        <div style="height:0.75rem" />
        <button class="btn secondary" disabled={busy || !nickname.trim() || code.length < 6} onClick={join}>
          ENTRAR
        </button>
      </Panel>
      {error && <p class="error">{error}</p>}
    </div>
  );
}
