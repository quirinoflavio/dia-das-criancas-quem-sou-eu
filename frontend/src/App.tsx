// App raiz: roteia pela fase do jogo e trata estados de borda.
import { useEffect, useState } from "preact/hooks";
import { Home } from "./Home";
import { Lobby } from "./Lobby";
import { RoundScreen } from "./RoundScreen";
import { RevealScreen, FinishedScreen } from "./RevealScreen";
import { useGameSocket } from "./useGameSocket";

function readCodeFromUrl(): string | null {
  const u = new URL(location.href);
  return u.searchParams.get("c");
}

export function App() {
  const [code, setCode] = useState<string | null>(readCodeFromUrl());
  const [entered, setEntered] = useState(false);
  const { state, error, closed, send } = useGameSocket(entered ? code : null);

  // Se chegou por link com ?c=, mostra a Home já com o código preenchido
  // até o usuário informar o apelido e entrar.
  const enter = (c: string) => { setCode(c); setEntered(true); };

  const leave = () => {
    // sai da sala e volta para a Home (sala permanece no servidor)
    setEntered(false);
    setCode(null);
    history.replaceState({}, "", "/");
  };

  if (closed) {
    return (
      <div class="wrap center">
        <h1>SALA ENCERRADA</h1>
        <p class="muted">Essa sala não existe mais ou o jogo já começou.</p>
        <button class="btn" onClick={() => { setEntered(false); setCode(null); }}>VOLTAR</button>
      </div>
    );
  }

  if (!entered || !code) {
    return <Home onEnter={enter} initialCode={code ?? undefined} />;
  }

  if (!state) {
    return (
      <div class="wrap center">
        <h1 class="blink">CONECTANDO…</h1>
        {error && <p class="error">{error}</p>}
      </div>
    );
  }

  return (
    <>
      {error && <p class="error wrap">{error}</p>}
      {(state.phase === "LOBBY" || state.phase === "GENERATING") && <Lobby state={state} />}
      {state.phase === "PLAYING" && <RoundScreen state={state} send={send} />}
      {state.phase === "REVEAL" && <RevealScreen state={state} send={send} />}
      {state.phase === "FINISHED" && <FinishedScreen state={state} send={send} onLeave={leave} />}
    </>
  );
}
