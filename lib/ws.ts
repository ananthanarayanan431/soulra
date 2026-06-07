export interface StatusEvent    { type: "status";        node: string; }
export interface ClarifyEvent   { type: "clarify";       question: string; }
export interface ChipsEvent     { type: "chips";         options: string[]; }
export interface TraditionDoneEvent {
  type: "tradition_done";
  tradition: string;
  author: string;
  quote: string;
  citation: string;
  analysis: string;
  source_passage: string;
}
export interface ActionStepEvent { type: "action_step"; n: string; title: string; body: string; }
export interface DoneEvent      { type: "done"; }
export interface ErrorEvent     { type: "error"; message: string; code: string; }

export type WsServerEvent =
  | StatusEvent
  | ClarifyEvent
  | ChipsEvent
  | TraditionDoneEvent
  | ActionStepEvent
  | DoneEvent
  | ErrorEvent;

export interface StartMessage         { type: "start";         situation: string; }
export interface ClarificationMessage { type: "clarification"; choice: string; }
export interface FollowupMessage      { type: "followup";      text: string; }

export type WsClientMessage = StartMessage | ClarificationMessage | FollowupMessage;
