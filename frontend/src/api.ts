// Identidade do jogador (token no localStorage) + cliente REST.
import type { RoomConfig } from "./types";

const KEY = "quemsoueu.identity";

export function getIdentity(): string {
  let t = localStorage.getItem(KEY);
  if (!t) {
    t = crypto.randomUUID().replace(/-/g, "");
    localStorage.setItem(KEY, t);
  }
  return t;
}

async function req(path: string, init: RequestInit = {}): Promise<any> {
  const headers: Record<string, string> = {
    "X-Identity": getIdentity(),
    ...(init.headers as Record<string, string> | undefined),
  };
  const res = await fetch(path, { ...init, headers });
  if (!res.ok) {
    let detail = res.statusText;
    try { detail = (await res.json()).detail ?? detail; } catch { /* ignore */ }
    throw new Error(detail);
  }
  return res.status === 204 ? null : res.json().catch(() => null);
}

export const api = {
  createRoom(nickname: string, config: RoomConfig) {
    return req("/api/rooms", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nickname, config }),
    });
  },
  joinRoom(code: string, nickname: string) {
    return req(`/api/rooms/${code}/join`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nickname }),
    });
  },
  updateConfig(code: string, config: RoomConfig) {
    return req(`/api/rooms/${code}/config`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ config }),
    });
  },
  uploadPhoto(code: string, file: File) {
    const fd = new FormData();
    fd.append("file", file);
    return req(`/api/rooms/${code}/photo`, { method: "POST", body: fd });
  },
  regen(code: string, playerId?: string) {
    return req(`/api/rooms/${code}/photo/regen`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ player_id: playerId ?? null }),
    });
  },
  start(code: string) {
    return req(`/api/rooms/${code}/start`, { method: "POST" });
  },
  close(code: string) {
    return req(`/api/rooms/${code}/close`, { method: "POST" });
  },
};

// URL de imagem já com o token (para a tag <img>).
export function imageUrl(path: string): string {
  const sep = path.includes("?") ? "&" : "?";
  return `${path}${sep}token=${getIdentity()}`;
}
