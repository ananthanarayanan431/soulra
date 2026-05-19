# Soulra — Plan C: Wisdom Engine (Claude API Integration)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
> **Prerequisite:** Plans A and B must be complete. All screens must exist with mock data.

**Goal:** Wire real AI responses into the conversation screen using the Anthropic Claude API, with proper streaming, source citations, action plans, and crisis signal detection — replacing all mock data in ConversationScreen with live responses.

**Architecture:** API route at `/api/chat` receives conversation history and returns a streaming response. The system prompt encodes Soulra's identity: cite sources, always end with 3-step action plan, distinct tradition voices, detect crisis signals. The client uses `fetch` with `ReadableStream` to stream tokens. Crisis detection runs server-side before streaming; if triggered, returns a structured crisis response instead of wisdom content. Prompt caching is used on the long system prompt to reduce cost.

**Tech Stack:** Anthropic SDK (`@anthropic-ai/sdk`), Next.js 14 Route Handlers, streaming Response, `ANTHROPIC_API_KEY` env var.

---

## File Map

```
app/
└── api/
    └── chat/
        └── route.ts           # POST handler — streams Claude response
lib/
├── prompts.ts                 # system prompt + response format instructions
├── crisis.ts                  # crisis signal detection (keyword + heuristic)
└── types.ts                   # shared Message, TraditionPerspective, ActionStep types
components/
└── conversation/
    └── StreamingResponse.tsx  # client component that streams from /api/chat
```

---

### Task 1: Install Anthropic SDK and set up env

**Files:**
- Modify: `package.json` (via npm install)
- Create: `.env.local`

- [ ] **Step 1: Install SDK**

```bash
npm install @anthropic-ai/sdk
```

Expected: `@anthropic-ai/sdk` appears in `package.json` dependencies.

- [ ] **Step 2: Create `.env.local`**

```bash
# .env.local
ANTHROPIC_API_KEY=your_key_here
```

Add `.env.local` to `.gitignore` if not already there:

```bash
grep -q ".env.local" .gitignore || echo ".env.local" >> .gitignore
```

- [ ] **Step 3: Commit**

```bash
git add package.json package-lock.json .gitignore
git commit -m "feat: install @anthropic-ai/sdk"
```

---

### Task 2: Shared types

**Files:**
- Create: `lib/types.ts`

- [ ] **Step 1: Create `lib/types.ts`**

```ts
// lib/types.ts

export interface Message {
  role: "user" | "assistant";
  content: string;
}

export interface TraditionPerspective {
  tradition: string;
  author: string;
  quote: string;
  explanation: string;
  citationBook: string;
  citationChapter: string;
}

export interface ActionStep {
  number: string;
  title: string;
  body: string;
}

export interface WisdomResponse {
  type: "wisdom";
  openingReflection: string;
  perspectives: TraditionPerspective[];
  actionPlan: ActionStep[];
}

export interface CrisisResponse {
  type: "crisis";
}

export interface ClarifyingResponse {
  type: "clarifying";
  question: string;
  options: string[];
}

export type SoulraResponse = WisdomResponse | CrisisResponse | ClarifyingResponse;
```

- [ ] **Step 2: Commit**

```bash
git add lib/types.ts
git commit -m "feat: add shared Soulra response types"
```

---

### Task 3: Crisis detection

**Files:**
- Create: `lib/crisis.ts`

- [ ] **Step 1: Create `lib/crisis.ts`**

```ts
// lib/crisis.ts
// Lightweight heuristic crisis detection.
// NOT a replacement for professional assessment — triggers a care redirect only.

const CRISIS_PHRASES = [
  "don't want to be here",
  "don't want to live",
  "want to die",
  "kill myself",
  "end my life",
  "no reason to live",
  "can't go on",
  "suicidal",
  "hurt myself",
  "harming myself",
];

export function detectCrisis(text: string): boolean {
  const lower = text.toLowerCase();
  return CRISIS_PHRASES.some(phrase => lower.includes(phrase));
}
```

- [ ] **Step 2: Commit**

```bash
git add lib/crisis.ts
git commit -m "feat: add crisis signal detection (keyword heuristic)"
```

---

### Task 4: System prompt

**Files:**
- Create: `lib/prompts.ts`

- [ ] **Step 1: Create `lib/prompts.ts`**

```ts
// lib/prompts.ts

export const SOULRA_SYSTEM_PROMPT = `You are Soulra, an AI wisdom companion that translates the world's great spiritual traditions into practical, situation-specific guidance.

## Your identity
You are warm, unhurried, and trustworthy — like a knowledgeable friend who has read everything and is never in a rush. You are not a therapist, not a preacher, and not a generic AI assistant.

## Conversation flow
1. When the user first shares a situation, ask ONE focused clarifying question before responding with wisdom. Format this as JSON with type "clarifying".
2. After the clarifying answer (or if the user explicitly asks to skip), respond with wisdom. Format this as JSON with type "wisdom".

## Response format — ALWAYS return valid JSON

### Clarifying (first response to a new situation):
{
  "type": "clarifying",
  "question": "Before I draw on the traditions — [one focused question about work/relationship/inner]?",
  "options": ["Option A", "Option B", "Option C", "Option D"]
}

### Wisdom response:
{
  "type": "wisdom",
  "openingReflection": "2-3 sentences acknowledging what you heard and framing why multiple perspectives matter here.",
  "perspectives": [
    {
      "tradition": "Stoic",
      "author": "Marcus Aurelius",
      "quote": "Direct quote from the text in double quotes",
      "explanation": "2-3 sentences applying this teaching to the user's specific situation.",
      "citationBook": "Meditations",
      "citationChapter": "Book 6, 13 — trans. Hays (2002)"
    }
  ],
  "actionPlan": [
    { "number": "01", "title": "Short title", "body": "One concrete, situation-specific action." },
    { "number": "02", "title": "Short title", "body": "One concrete, situation-specific action." },
    { "number": "03", "title": "Short title", "body": "One concrete, situation-specific action." }
  ]
}

## Rules — non-negotiable
- Always cite exactly: tradition + book/text + chapter/verse + translator if applicable.
- NEVER fabricate a citation. If uncertain, say "This reflects the spirit of [tradition]" and note you are paraphrasing.
- Always include 2-3 perspectives from DISTINCT traditions. Do not homogenise or blend them.
- The actionPlan must have EXACTLY 3 steps, each situation-specific and actionable today.
- Preserve each tradition's distinct voice. Zen's view of suffering is not Stoicism's view. Both differ from Vedanta.
- Never add philosophy or quotes when a user is in distress — the crisis path is handled separately.
- You cover: Vedanta, Stoicism, Buddhism, Taoism, Sufism, Christian mysticism, Jewish wisdom, Zen, and other lineages.`;
```

- [ ] **Step 2: Commit**

```bash
git add lib/prompts.ts
git commit -m "feat: add Soulra system prompt with JSON response format"
```

---

### Task 5: Chat API route

**Files:**
- Create: `app/api/chat/route.ts`

- [ ] **Step 1: Create `app/api/chat/route.ts`**

```ts
// app/api/chat/route.ts
import Anthropic from "@anthropic-ai/sdk";
import { NextRequest } from "next/server";
import { SOULRA_SYSTEM_PROMPT } from "@/lib/prompts";
import { detectCrisis } from "@/lib/crisis";
import type { Message } from "@/lib/types";

const client = new Anthropic();

export async function POST(req: NextRequest) {
  const { messages }: { messages: Message[] } = await req.json();

  // Check last user message for crisis signals
  const lastUserMessage = [...messages].reverse().find(m => m.role === "user");
  if (lastUserMessage && detectCrisis(lastUserMessage.content)) {
    return Response.json({ type: "crisis" });
  }

  // Stream response from Claude
  const stream = await client.messages.stream({
    model: "claude-sonnet-4-6",
    max_tokens: 2048,
    system: [
      {
        type: "text",
        text: SOULRA_SYSTEM_PROMPT,
        cache_control: { type: "ephemeral" },
      },
    ],
    messages: messages.map(m => ({ role: m.role, content: m.content })),
  });

  // Collect full response (JSON parsing requires complete text)
  let fullText = "";
  const encoder = new TextEncoder();

  const readable = new ReadableStream({
    async start(controller) {
      for await (const chunk of stream) {
        if (chunk.type === "content_block_delta" && chunk.delta.type === "text_delta") {
          fullText += chunk.delta.text;
          controller.enqueue(encoder.encode(chunk.delta.text));
        }
      }
      controller.close();
    },
  });

  return new Response(readable, {
    headers: {
      "Content-Type": "text/plain; charset=utf-8",
      "Transfer-Encoding": "chunked",
    },
  });
}
```

- [ ] **Step 2: Test the route manually**

Start dev server and test with curl:

```bash
npm run dev &
sleep 5
curl -s -X POST http://localhost:3000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"I keep saying yes to things I don'\''t want to do."}]}' \
  | head -200
kill %1
```

Expected: JSON streaming back with `type: "clarifying"` and a question.

- [ ] **Step 3: Commit**

```bash
git add app/api/chat/route.ts
git commit -m "feat: add /api/chat route with Claude streaming and crisis detection"
```

---

### Task 6: Streaming conversation client

**Files:**
- Create: `components/conversation/StreamingResponse.tsx`
- Modify: `components/screens/ConversationScreen.tsx`

- [ ] **Step 1: Create `StreamingResponse.tsx`**

```tsx
// components/conversation/StreamingResponse.tsx
"use client";
import { useState, useCallback } from "react";
import { ClarifyingPause } from "./ClarifyingPause";
import { TraditionCard } from "./TraditionCard";
import { ActionPlan } from "./ActionPlan";
import type { Message, SoulraResponse } from "@/lib/types";

interface StreamingResponseProps {
  messages: Message[];
  onCrisis: () => void;
  onClarified: (answer: string) => void;
}

export function StreamingResponse({ messages, onCrisis, onClarified }: StreamingResponseProps) {
  const [response, setResponse] = useState<SoulraResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [rawText, setRawText] = useState("");

  const fetchResponse = useCallback(async (msgs: Message[]) => {
    setLoading(true);
    setRawText("");
    setResponse(null);

    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messages: msgs }),
    });

    if (!res.ok) { setLoading(false); return; }
    if (!res.body) { setLoading(false); return; }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let accumulated = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      accumulated += decoder.decode(value, { stream: true });
      setRawText(accumulated);
    }

    try {
      const parsed: SoulraResponse = JSON.parse(accumulated);
      if (parsed.type === "crisis") onCrisis();
      setResponse(parsed);
    } catch {
      // streaming partial — show raw text while parsing
    }
    setLoading(false);
  }, [onCrisis]);

  if (loading) {
    return (
      <div className="flex gap-3.5">
        <div className="w-8 h-8 rounded-full border border-ink flex items-center justify-center font-serif text-sm flex-shrink-0">S</div>
        <div className="font-serif text-[19px] italic text-muted animate-pulse">
          {rawText || "Sitting with this…"}
        </div>
      </div>
    );
  }

  if (!response) return null;

  if (response.type === "clarifying") {
    return (
      <ClarifyingPause
        question={response.question}
        options={response.options}
        onSelect={onClarified}
      />
    );
  }

  if (response.type === "wisdom") {
    return (
      <div className="flex flex-col gap-4">
        <div className="text-sm leading-[1.7] max-w-[640px]">{response.openingReflection}</div>
        {response.perspectives.map((p, i) => (
          <TraditionCard
            key={i}
            index={i + 1}
            total={response.perspectives.length}
            tradition={p.tradition}
            author={p.author}
            quote={p.quote}
            explanation={p.explanation}
            citationBook={p.citationBook}
            citationChapter={p.citationChapter}
            initiallyExpanded={i === 0}
          />
        ))}
        <ActionPlan steps={response.actionPlan} />
      </div>
    );
  }

  return null;
}
```

- [ ] **Step 2: Wire into `ConversationScreen.tsx`**

Replace the static mock content in `ConversationScreen.tsx` with a live conversation state machine:

```tsx
// components/screens/ConversationScreen.tsx
"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { Sidebar } from "@/components/layout/Sidebar";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { StreamingResponse } from "@/components/conversation/StreamingResponse";
import type { Message } from "@/lib/types";

type ConversationState = "idle" | "waiting_clarification" | "responded" | "crisis";

export function ConversationScreen() {
  const router = useRouter();
  const [inputValue, setInputValue] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [state, setState] = useState<ConversationState>("idle");

  function handleSend() {
    if (!inputValue.trim()) return;
    const newMessages: Message[] = [...messages, { role: "user", content: inputValue }];
    setMessages(newMessages);
    setInputValue("");
    setState("waiting_clarification");
  }

  function handleClarified(answer: string) {
    const newMessages: Message[] = [...messages, { role: "user", content: answer }];
    setMessages(newMessages);
    setState("responded");
  }

  function handleCrisis() {
    router.push("/crisis");
  }

  const lastUserMessage = [...messages].reverse().find(m => m.role === "user");

  return (
    <div className="flex h-screen bg-paper overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">

        <div className="px-9 py-4 border-b border-line flex items-center justify-between">
          <div>
            <div className="font-serif text-base font-medium">
              {lastUserMessage ? `"${lastUserMessage.content.slice(0, 40)}…"` : "New conversation"}
            </div>
            <div className="font-mono text-[10px] text-muted mt-0.5">
              {messages.length > 0 ? `${Math.ceil(messages.length / 2)} exchanges` : "Start by sharing what's on your mind"}
            </div>
          </div>
          {messages.length > 0 && <Button small>◇ Save to journal</Button>}
        </div>

        <div className="flex-1 overflow-auto px-9 py-8 flex flex-col gap-7 max-w-[820px] self-center w-full">
          {messages.length === 0 && (
            <div className="font-serif text-[28px] italic text-muted text-center mt-20">
              What is asking for your attention today?
            </div>
          )}

          {messages.map((msg, i) => (
            <div key={i}>
              {msg.role === "user" && (
                <div className="self-end max-w-[520px] ml-auto p-4 bg-paper-alt border border-line text-sm leading-relaxed"
                     style={{ borderRadius: "14px 14px 2px 14px" }}>
                  {msg.content}
                </div>
              )}
            </div>
          ))}

          {messages.length > 0 && (
            <StreamingResponse
              messages={messages}
              onCrisis={handleCrisis}
              onClarified={handleClarified}
            />
          )}
        </div>

        <div className="px-9 py-4 border-t border-line">
          <div className="max-w-[820px] mx-auto flex gap-3">
            <div className="flex-1">
              <input
                className="w-full border border-ink rounded-xl px-4 py-3 text-sm bg-paper font-sans outline-none focus:ring-1 focus:ring-ink"
                placeholder="Tell Soulra what's on your mind…"
                value={inputValue}
                onChange={e => setInputValue(e.target.value)}
                onKeyDown={e => e.key === "Enter" && !e.shiftKey && handleSend()}
              />
            </div>
            <Button primary small onClick={handleSend}>↵</Button>
          </div>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Test end-to-end**

```bash
npm run dev &
sleep 5
# Open http://localhost:3000/chat in browser
# Type: "I keep saying yes to things I don't want to do"
# Verify: clarifying question appears with chip options
# Click a chip
# Verify: wisdom response appears with traditions, citations, action plan
kill %1
```

Expected: full conversation flow works with real Claude API responses.

- [ ] **Step 4: Test crisis path**

```bash
npm run dev &
sleep 5
# Type: "I don't want to be here anymore"
# Verify: redirected to /crisis page
kill %1
```

Expected: crisis screen shown, no wisdom response.

- [ ] **Step 5: Build check**

```bash
npm run build 2>&1 | tail -20
```

Expected: build succeeds with no TypeScript errors.

- [ ] **Step 6: Commit**

```bash
git add app/api/ components/conversation/StreamingResponse.tsx components/screens/ConversationScreen.tsx
git commit -m "feat: wire Claude API streaming into conversation screen with crisis detection"
```

---

## Self-Review

**Spec coverage:**
- ✅ Claude API integration (claude-sonnet-4-6)
- ✅ Streaming response
- ✅ Prompt caching on system prompt (ephemeral cache_control)
- ✅ Clarifying question before wisdom (system prompt enforces it)
- ✅ 2-3 tradition perspectives per response (system prompt enforces it)
- ✅ Citations: tradition + book + chapter (system prompt enforces it + TraditionCard displays them)
- ✅ 3-step action plan (system prompt enforces EXACTLY 3)
- ✅ Distinct tradition voices (system prompt enforces no blending)
- ✅ Never fabricate citations (system prompt instruction)
- ✅ Crisis detection: server-side keyword check → redirects to /crisis
- ✅ Crisis path: no philosophy, redirects to CrisisScreen

**Placeholder scan:** None.

**Type consistency:** `Message`, `TraditionPerspective`, `ActionStep`, `SoulraResponse` all defined in `lib/types.ts` and imported consistently across `route.ts`, `StreamingResponse.tsx`, `TraditionCard.tsx`, and `ActionPlan.tsx`.
