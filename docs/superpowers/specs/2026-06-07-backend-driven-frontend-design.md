# Backend-Driven Frontend: Remove All Hardcoded Data

**Date:** 2026-06-07  
**Status:** Approved

## Problem

The frontend contains hardcoded data throughout:
- `HomeScreen`: hardcoded "today's teaching" card, "from the traditions" card, prompt chips
- `DailyScreen`: fully mocked — `DAYS` array, reflection default text, morning lesson, week theme
- `JournalScreen`: fully mocked — `TAGS`, `TRADITION_COUNTS`, `LESSONS` arrays, revisit nudge, stats
- `ConversationScreen`: `STATUS_LABELS` node-name → display-string map

Additionally, the WebSocket handler never persists conversations to the database. The `conversations` and `action_steps` tables exist but remain empty.

## Approach

Approach A — derive practice content from existing conversation data. No new LLM calls. When a conversation completes, the backend persists it and auto-creates a 7-day practice arc from the action steps and tradition cards returned by the synthesize node.

---

## Section 1: Backend Persistence + New Models

### WebSocket Handler Changes

After `synthesize` node `on_chain_end`, the handler persists:
1. `Conversation` row (thread_id, situation, clarify_q, clarify_ans, completed_at)
2. `ActionStep` rows (step_number, title, body) — already modelled
3. `TraditionCard` rows (new model, card_order)
4. Auto-creates `PracticeArc` + `PracticeDay` rows

The clarify_q and clarify_ans are captured during the clarify phase (already available in graph state).

### New Database Models

**`TraditionCard`** (table: `tradition_cards`)
- `id: UUID PK`
- `conversation_id: UUID FK → conversations CASCADE`
- `card_order: int` (0-indexed insertion order)
- `tradition: str`
- `author: str`
- `quote: str`
- `citation: str`
- `analysis: str`
- `source_passage: str`

**`PracticeArc`** (table: `practice_arcs`)
- `id: UUID PK`
- `conversation_id: UUID FK → conversations CASCADE UNIQUE` (one arc per conversation)
- `theme: str` (= `conversation.situation[:120]`)
- `status: str` enum `active | completed`, default `active`
- `current_day: int` default `1` (1–7, advances when a day is completed)
- `created_at: datetime`

**`PracticeDay`** (table: `practice_days`)
- `id: UUID PK`
- `arc_id: UUID FK → practice_arcs CASCADE`
- `day_number: int` (1–7)
- `day_label: str` (e.g. "Mon", computed from arc.created_at + day_number offset)
- `task_title: str` (from `ActionStep.title`, cycled if < 7 steps; day 7 always "Reflection & integration")
- `task_body: str` (from `ActionStep.body`)
- `morning_quote: str` (from `TraditionCard.quote`, cycled by `(day_number-1) % len(cards)`)
- `morning_author: str`
- `morning_citation: str`
- `morning_analysis: str`
- `evening_prompt: str` (= `f"Did '{task_title}' show up today, even once? What did you notice?"`)
- `reflection_text: str | None`
- `reflection_at: datetime | None`
- `completed: bool` default `False`

**Practice arc day-building rules:**
- If 3 action steps: days 1–3 map to steps 1–3, days 4–6 repeat steps 1–3, day 7 = "Reflection & integration" with body = "Sit with what emerged this week."
- If 7 steps: 1-to-1 mapping.
- Day 7 always overrides to "Reflection & integration" regardless of step count.
- Morning cards cycle: day N uses `tradition_cards[(N-1) % len(cards)]`.

**`JournalEntry`** (table: `journal_entries`)
- `id: UUID PK`
- `conversation_id: UUID FK → conversations SET NULL, nullable`
- `quote: str`
- `author: str`
- `tradition: str`
- `citation: str`
- `tags: JSONB` (list of strings, default `[]`)
- `applied: bool` default `False`
- `created_at: datetime`
- `last_revisited_at: datetime | None`

### Migration

One Alembic migration (`0002_practice_journal.py`) adds all four tables: `tradition_cards`, `practice_arcs`, `practice_days`, `journal_entries`.

---

## Section 2: New API Endpoints

### Config (static UI strings)

**`GET /api/v1/config`**
```json
{
  "status_labels": {
    "intake": "Understanding your situation…",
    "retrieve": "Searching wisdom traditions…",
    "rerank": "Refining passages…",
    "grade_docs": "Evaluating relevance…",
    "rewrite_query": "Deepening the search…",
    "clarify": "Preparing a question…",
    "retrieve_refined": "Searching further…",
    "rerank_refined": "Refining results…",
    "synthesize": "Drawing from the traditions…"
  },
  "fallback_status_label": "Consulting the traditions…",
  "suggestions": [
    "I keep saying yes when I mean no",
    "I'm carrying grief that won't move",
    "Who am I outside this role?",
    "I feel stuck and I don't know why"
  ]
}
```
Static — no DB, no auth. Returned from a constant in `soulra/config.py`.

### Daily Teaching

**`GET /api/v1/daily-teaching`**  
Returns one passage from the vector DB, deterministically seeded by the current UTC date (date string hashed to an offset). If vectorstore is empty, returns `null`.

```json
{
  "tradition": "Stoic",
  "author": "Marcus Aurelius",
  "quote": "You always own the option of having no opinion.",
  "citation": "Meditations 6.13",
  "explore_situation": "You always own the option of having no opinion."
}
```
`explore_situation` is the quote used as a pre-filled chat situation link.

### Practice

**`GET /api/v1/practice/active`**  
Returns the most recent arc with `status=active`, or `null`.

```json
{
  "id": "uuid",
  "theme": "I keep saying yes when I mean no",
  "status": "active",
  "current_day": 4,
  "days_into_arc": "4 days into a 7-day arc",
  "days": [
    {
      "day_number": 1,
      "day_label": "Mon",
      "task_title": "Notice the moment of yes",
      "task_body": "...",
      "morning_quote": "...",
      "morning_author": "...",
      "morning_citation": "...",
      "morning_analysis": "...",
      "evening_prompt": "...",
      "reflection_text": null,
      "completed": true,
      "state": "done"
    }
  ]
}
```

`state` field per day is computed server-side: `"done"` if `completed`, `"today"` if `day_number == current_day`, else `"future"`.  
`days_into_arc` is a pre-formatted string: `f"{current_day} days into a 7-day arc"`.

**`POST /api/v1/practice/{conversation_id}`**  
Idempotent. Creates an arc from the conversation's persisted action steps and tradition cards. Returns existing arc if already created. 404 if conversation not found.

**`PATCH /api/v1/practice/{arc_id}/days/{day_number}/complete`**  
Marks the day as `completed=True`. Advances `arc.current_day` to `day_number + 1` (max 7). If all 7 days complete, sets `arc.status = "completed"`. Returns updated `PracticeArcOut`.

**`PATCH /api/v1/practice/{arc_id}/days/{day_number}/reflect`**  
Body: `{"text": "..."}`. Saves reflection. Returns `204`.

### Journal

**`GET /api/v1/journal?limit=50&offset=0&tag=career`**
```json
{
  "data": {
    "entries": [...],
    "stats": {
      "total": 12,
      "applied_this_month": 3,
      "last_revisited_days_ago": 4,
      "tags": [{"name": "all", "count": 12}, {"name": "career", "count": 5}],
      "traditions": [{"name": "Stoic", "count": 5}]
    }
  }
}
```

**`POST /api/v1/journal`**  
Body: `{"conversation_id": "uuid", "tradition_card_index": 0}`. Saves the specified tradition card as a journal entry. 404 if card not found. Returns `JournalEntryOut`.

**`PATCH /api/v1/journal/{id}`**  
Body: `{"tags": [...], "applied": true}` (both optional). Returns updated entry.

**`DELETE /api/v1/journal/{id}`** — 204.

---

## Section 3: Frontend Changes

### `lib/api.ts`

Add fetch functions (all graceful — return null/empty on error):
- `getConfig()` → `UIConfig`
- `getDailyTeaching()` → `DailyTeaching | null`
- `getDailyPractice()` → `PracticeArc | null`
- `completeDay(arcId, dayNumber)` → void
- `reflectDay(arcId, dayNumber, text)` → void
- `listJournal(opts)` → `{entries, stats}`
- `saveJournalEntry(conversationId, traditionIndex)` → `JournalEntry`
- `updateJournalEntry(id, patch)` → `JournalEntry`
- `deleteJournalEntry(id)` → void

`formatRelativeDate` stays — it is a display-layer formatter, not business logic.

### `HomeScreen.tsx`

Server component. Remove:
- Hardcoded "today's teaching" block
- Hardcoded "from the traditions" block
- Hardcoded chip strings

Add:
- `const teaching = await getDailyTeaching()`
- `const { suggestions } = await getConfig()`
- Render teaching from API, or omit card if `null`
- Render suggestion chips from API array

### `DailyScreen.tsx`

Split into:
- `DailyScreen` server component — fetches `getDailyPractice()`, renders static layout
- `DailyClient` client component — handles reflection textarea state and complete/reflect button actions

Remove: `DAYS` constant, hardcoded `reflection` default, hardcoded theme string, hardcoded "4 days into a 7-day arc" string, all static card content.

Add: Empty state when `getDailyPractice()` returns `null` ("No active practice. Start a conversation to begin a 7-day arc.").

### `JournalScreen.tsx`

Remove: `TAGS`, `TRADITION_COUNTS`, `LESSONS` constants, hardcoded revisit nudge content, hardcoded stats string.

Tag filter becomes a URL search param (`?tag=career`) — `JournalScreen` accepts `searchParams` and passes `tag` to `listJournal()`. No client state needed for tag filtering.

Add: Empty state variant (already exists as `<EmptyState />`) shown when `stats.total === 0`.  
The hardcoded Epictetus quote in EmptyState is replaced by `getDailyTeaching()` output.

### `ConversationScreen.tsx`

Remove: `STATUS_LABELS` constant.  
Add: Accept `statusLabels: Record<string, string>` and `fallbackStatusLabel: string` props.  
`ThinkingIndicator` receives these as props.

### `app/chat/page.tsx`

Convert to fetch config server-side:
```tsx
export default async function ChatPage() {
  const config = await getConfig();
  return (
    <Suspense fallback={<Loading />}>
      <ConversationScreen
        statusLabels={config.status_labels}
        fallbackStatusLabel={config.fallback_status_label}
      />
    </Suspense>
  );
}
```

---

## What Stays on the Frontend

- `formatRelativeDate` — pure view formatter
- Error/loading UI states — frontend rendering concern
- `useSoulraChat` reducer logic — WebSocket state machine, not business logic
- CSS, layout, component structure

---

## Out of Scope

- Auth / user sessions (all endpoints are currently unauthed)
- Journal "save from ConversationScreen" UX flow (button exists but not wired; tracked separately)
- Revisit scheduling logic (when to surface journal nudges)
