"use client";
import { useEffect, useReducer, useRef } from "react";
import { useAuth } from "@clerk/nextjs";
import type { WsServerEvent, WsClientMessage } from "@/lib/ws";

export interface TraditionCard {
  tradition: string;
  author: string;
  quote: string;
  citation: string;
  analysis: string;
  source_passage: string;
}

export interface ActionStep {
  n: string;
  title: string;
  body: string;
}

export type ChatPhase =
  | "connecting"
  | "thinking"
  | "clarifying"
  | "responding"
  | "done"
  | "error";

export interface ChatState {
  phase: ChatPhase;
  statusNode: string;
  clarifyQuestion: string | null;
  clarifyOptions: string[];
  clarifyAnswer: string | null;
  traditionCards: TraditionCard[];
  actionSteps: ActionStep[];
  error: string | null;
  conversationId: string | null;
}

type Action =
  | { type: "OPEN" }
  | { type: "EVENT"; event: WsServerEvent }
  | { type: "CLARIFICATION_SENT"; choice: string }
  | { type: "WS_ERROR" };

const INITIAL: ChatState = {
  phase: "connecting",
  statusNode: "",
  clarifyQuestion: null,
  clarifyOptions: [],
  clarifyAnswer: null,
  traditionCards: [],
  actionSteps: [],
  error: null,
  conversationId: null,
};

function reducer(state: ChatState, action: Action): ChatState {
  switch (action.type) {
    case "OPEN":
      return { ...state, phase: "thinking" };

    case "CLARIFICATION_SENT":
      return { ...state, phase: "responding", clarifyAnswer: action.choice };

    case "WS_ERROR":
      return { ...state, phase: "error", error: "Connection failed. Please try again." };

    case "EVENT": {
      const e = action.event;
      switch (e.type) {
        case "status":
          return { ...state, statusNode: e.node };
        case "clarify":
          return { ...state, phase: "clarifying", clarifyQuestion: e.question };
        case "chips":
          return { ...state, clarifyOptions: e.options };
        case "tradition_done":
          return {
            ...state,
            traditionCards: [
              ...state.traditionCards,
              {
                tradition: e.tradition,
                author: e.author,
                quote: e.quote,
                citation: e.citation,
                analysis: e.analysis,
                source_passage: e.source_passage,
              },
            ],
          };
        case "action_step":
          return {
            ...state,
            actionSteps: [...state.actionSteps, { n: e.n, title: e.title, body: e.body }],
          };
        case "done":
          return { ...state, phase: "done", conversationId: e.conversation_id ?? null };
        case "error":
          return { ...state, phase: "error", error: e.message };
        default:
          return state;
      }
    }

    default:
      return state;
  }
}

export function useSoulraChat(situation: string) {
  const [state, dispatch] = useReducer(reducer, INITIAL);
  const wsRef = useRef<WebSocket | null>(null);
  const { getToken } = useAuth();

  useEffect(() => {
    if (!situation) return;

    let cancelled = false;
    let ws: WebSocket | null = null;

    (async () => {
      const token = await getToken();
      if (cancelled) return;

      const WS_BASE = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000";
      const url = token
        ? `${WS_BASE}/ws/chat?token=${encodeURIComponent(token)}`
        : `${WS_BASE}/ws/chat`;

      ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        const msg: WsClientMessage = { type: "start", situation };
        ws!.send(JSON.stringify(msg));
        dispatch({ type: "OPEN" });
      };

      ws.onmessage = (ev: MessageEvent<string>) => {
        try {
          const event = JSON.parse(ev.data) as WsServerEvent;
          dispatch({ type: "EVENT", event });
        } catch {
          // malformed message — ignore
        }
      };

      ws.onerror = () => dispatch({ type: "WS_ERROR" });
    })();

    return () => {
      cancelled = true;
      ws?.close();
      wsRef.current = null;
    };
  }, [situation, getToken]);

  function sendClarification(choice: string) {
    const msg: WsClientMessage = { type: "clarification", choice };
    wsRef.current?.send(JSON.stringify(msg));
    dispatch({ type: "CLARIFICATION_SENT", choice });
  }

  return { state, sendClarification };
}
