# Today Page Redesign

**Date:** 2026-06-09
**Status:** Approved

## Problem

The `/home` page ("Today" in sidebar) and `/chat` page ("New conversation") both render a chat textarea, creating redundant UI. The `/home` page also repeats the "how it works" flow steps already present on the landing page (`/`). As a result, "Today" has no distinct purpose — it's a diluted chat page rather than a meaningful daily anchor.

## Goal

Transform `/home` into a **daily anchor page**: the first thing a user sees that orients them to the day — the morning teaching, the evening question, and a single clear path to begin a new conversation. Remove all chat input and redundant explanatory content from this page.

## Design

### Layout (active practice arc)

```
[Sidebar] | MONDAY · JUNE 9                          [monospace date, small]
          |
          | What is asking for your                  [serif, ~36px, display]
          | attention today?
          |
          | ──────────────────────────────────────── [thin rule]
          |
          | MORNING · TODAY'S PRACTICE               [mono label]
          | "morning quote in large italic serif"    [serif, ~22px]
          | ↓ Author · Citation                      [mono, accent color]
          | morning_analysis paragraph               [body, muted]
          |
          | EVENING · REFLECTION                     [mono label, mt-6]
          | evening_prompt in medium italic           [serif, ~18px]
          |
          | Begin a new conversation →   See this week →   [text-links, mono]
          |
          | ──────────────────────────────────────── [thin rule]
          |
          | RECENT CONVERSATIONS                     [grid, 3 cards, existing]
```

### Layout (no arc yet)

```
[Sidebar] | What is asking for your                  [same display heading]
          | attention today?
          |
          | Complete a conversation to begin          [muted body text]
          | your 7-day practice thread.
          |
          | Begin a conversation →                    [primary button]
```

### What is removed from `/home`

- `SituationInput` textarea component
- Prompt chips ("I keep saying yes when I mean no…")
- "How Soulra works" `FlowStep` grid
- `TraditionsPanel` component (belongs on `/traditions`)
- `PracticePanel` component (replaced by inline morning/evening display)

### What is kept

- `RecentConversations` grid at the bottom (useful quick-access)
- Sidebar (unchanged)

## Data

`HomeScreen` already fetches `arc` via `getActivePractice()`. The today day is derived as:

```ts
const today = arc.days.find(d => d.state === "today") ?? arc.days[arc.current_day - 1];
```

Fields used: `today.morning_quote`, `today.morning_author`, `today.morning_citation`, `today.morning_analysis`, `today.evening_prompt`, `today.day_label`.

No new API calls needed.

## Files changed

- `components/screens/HomeScreen.tsx` — primary change, remove panels/input, add morning/evening display

## Out of scope

- `/daily` page — no changes
- `/chat` page — no changes
- Sidebar nav — no changes
