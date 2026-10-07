// Tipos espelhando a projeção do servidor (app/realtime/projection.py).

export type Phase = "LOBBY" | "GENERATING" | "PLAYING" | "REVEAL" | "FINISHED";
export type DisplayMode =
  | "CHILD_ONLY" | "GENERATED_ONLY" | "BOTH"
  | "SEQ_CHILD_FIRST" | "SEQ_GENERATED_FIRST" | "RANDOM";
export type RevealMode = "END_OF_GAME" | "PER_ROUND";
export type GenStatus = "NONE" | "PENDING" | "GENERATING" | "READY" | "FAILED";

export interface PlayerView {
  id: string;
  nickname: string;
  is_host: boolean;
  connected: boolean;
  has_photo: boolean;
  gen_status: GenStatus;
  score: number;
}

export interface RoomConfig {
  display_mode: DisplayMode;
  reveal_mode: RevealMode;
  targets_per_round: number;
  max_players: number;
}

export interface TargetImages {
  target_id: string;
  mode: DisplayMode;
  seq_stage: number | null;
  child: string | null;
  generated: string | null;
}

export interface RoundView {
  index: number;
  status: string;
  targets: TargetImages[];
  vote_progress: { completed: number; total: number };
  my_votes: Record<string, string | null>;
}

export interface RevealTarget {
  target_id: string;
  nickname: string;
  child: string | null;
  generated: string | null;
  votes: {
    voter_id: string; voter_nickname: string;
    guess_id: string; guess_nickname: string; correct: boolean;
  }[];
}

export interface ScoreRow {
  player_id: string; nickname: string; score: number; position: number;
}

export interface RoomState {
  type: "room_state";
  code: string;
  phase: Phase;
  you: string;
  is_host: boolean;
  config: RoomConfig;
  players: PlayerView[];
  num_rounds: number;
  current_round_idx: number;
  round?: RoundView;
  reveal?: { round_index: number; targets: RevealTarget[] };
  reveals?: { round_index: number; targets: RevealTarget[] }[];
  scoreboard?: ScoreRow[];
  winners?: string[];
}
