// Hook de estado de jogo via WebSocket, com reconexão automática.
import { useEffect, useRef, useState } from "preact/hooks";
import { getIdentity } from "./api";
import type { RoomState } from "./types";

export interface GameSocket {
  state: RoomState | null;
  error: string | null;
  closed: boolean; // sala encerrada / não encontrada
  send: (msg: object) => void;
}

export function useGameSocket(code: string | null): GameSocket {
  const [state, setState] = useState<RoomState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [closed, setClosed] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const retryRef = useRef<number>(0);
  const stopRef = useRef(false);

  useEffect(() => {
    if (!code) return;
    stopRef.current = false;

    const connect = () => {
      if (stopRef.current) return;
      const proto = location.protocol === "https:" ? "wss" : "ws";
      const url = `${proto}://${location.host}/ws/rooms/${code}?token=${getIdentity()}`;
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onmessage = (ev) => {
        const msg = JSON.parse(ev.data);
        if (msg.type === "room_state") { setState(msg); setError(null); }
        else if (msg.type === "error") { setError(msg.message); }
        // pong ignorado
      };
      ws.onclose = (ev) => {
        if (ev.code === 4404) { setClosed(true); return; }
        if (stopRef.current) return;
        const delay = Math.min(1000 * 2 ** retryRef.current, 8000);
        retryRef.current++;
        setTimeout(connect, delay);
      };
      ws.onopen = () => { retryRef.current = 0; };
    };

    connect();
    const ping = setInterval(() => {
      wsRef.current?.readyState === WebSocket.OPEN &&
        wsRef.current.send(JSON.stringify({ type: "ping" }));
    }, 25000);

    return () => {
      stopRef.current = true;
      clearInterval(ping);
      wsRef.current?.close();
    };
  }, [code]);

  const send = (msg: object) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(msg));
    }
  };

  return { state, error, closed, send };
}
