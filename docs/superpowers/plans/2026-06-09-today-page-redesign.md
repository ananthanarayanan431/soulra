# Today Page Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite `HomeScreen` to be a daily anchor page — displaying today's morning quote and evening prompt as content, replacing the chat textarea and redundant "how it works" section.

**Architecture:** Single file change to `components/screens/HomeScreen.tsx`. Remove `SituationInput`, `FlowStep`, `TraditionsPanel`, `PracticePanel`, and prompt chips. Add `TodayPractice` and `EmptyPractice` sub-components. No new API calls — `getActivePractice()` is already fetched.

**Tech Stack:** Next.js (App Router), React Server Components, Tailwind CSS, TypeScript

---

### Task 1: Rewrite HomeScreen.tsx

**Files:**
- Modify: `components/screens/HomeScreen.tsx`

The full replacement. The file currently imports `SituationInput`, `Chip`, and `listTraditions` — all of which are removed. It exports one `HomeScreen` async server component.

- [ ] **Step 1: Replace the file contents**

Open `components/screens/HomeScreen.tsx` and replace its entire contents with:

```tsx
import Link from "next/link";
import { Sidebar } from "@/components/layout";
import {
  listConversations,
  getActivePractice,
  formatRelativeDate,
} from "@/lib/api";
import type { Conversation, PracticeDay } from "@/lib/api";

function TodayPractice({ today }: { today: PracticeDay }) {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <div className="font-mono text-[10px] text-muted uppercase tracking-widest mb-3">
          morning · today&apos;s practice
        </div>
        <div className="font-serif text-[22px] leading-[1.4] italic">
          &ldquo;{today.morning_quote}&rdquo;
        </div>
        <div className="font-mono text-[10px] text-accent mt-2">
          &darr; {today.morning_author} &middot; {today.morning_citation}
        </div>
        <p className="text-[13px] text-muted leading-[1.7] mt-3 max-w-[600px]">
          {today.morning_analysis}
        </p>
      </div>

      <div className="border-t border-line pt-5">
        <div className="font-mono text-[10px] text-muted uppercase tracking-widest mb-2">
          evening · reflection
        </div>
        <div className="font-serif text-[18px] leading-[1.4] italic text-ink">
          {today.evening_prompt}
        </div>
      </div>

      <div className="flex gap-5 items-center">
        <Link href="/chat" className="font-mono text-[11px] text-accent hover:underline">
          Begin a new conversation →
        </Link>
        <Link href="/daily" className="font-mono text-[11px] text-muted hover:text-ink transition-colors">
          See this week →
        </Link>
      </div>
    </div>
  );
}

function EmptyPractice() {
  return (
    <div className="flex flex-col gap-4">
      <p className="text-[14px] text-muted leading-relaxed max-w-[480px]">
        Complete a conversation to begin your 7-day practice thread — morning teachings
        drawn from what the traditions said to you, evening questions to close the day.
      </p>
      <Link href="/chat" className="font-mono text-[11px] text-accent hover:underline">
        Begin a conversation →
      </Link>
    </div>
  );
}

function RecentConversations({ conversations }: { conversations: Conversation[] }) {
  if (conversations.length === 0) return null;

  return (
    <div>
      <div className="font-mono text-[10px] text-muted uppercase tracking-widest mb-3">
        recent conversations
      </div>
      <div className="grid grid-cols-3 gap-3">
        {conversations.map(c => (
          <Link key={c.id} href={`/chat?id=${c.id}`}>
            <div className="border border-line rounded-xl p-4 bg-paper-alt hover:border-ink transition-colors cursor-pointer h-full">
              <div className="font-serif text-[14px] leading-snug italic">
                &ldquo;{c.situation.slice(0, 65)}{c.situation.length > 65 ? "…" : ""}&rdquo;
              </div>
              <div className="flex justify-between items-center mt-3">
                <span className="font-mono text-[9px] text-muted">
                  {formatRelativeDate(c.created_at)}
                </span>
                <span className="font-mono text-[9px] text-accent">
                  {c.tradition_cards.length} voice{c.tradition_cards.length !== 1 ? "s" : ""}
                </span>
              </div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}

export async function HomeScreen() {
  const [conversations, arc] = await Promise.all([
    listConversations(3),
    getActivePractice(),
  ]);

  const today = arc
    ? (arc.days.find(d => d.state === "today") ?? arc.days[arc.current_day - 1])
    : null;

  const dateLabel = new Date().toLocaleDateString("en-US", {
    weekday: "long",
    month: "long",
    day: "numeric",
  }).toUpperCase();

  return (
    <div className="flex h-screen bg-paper overflow-hidden">
      <Sidebar />

      <div className="flex-1 overflow-auto px-10 py-10">
        <div className="font-mono text-[10px] text-muted uppercase tracking-widest mb-5">
          {dateLabel}
        </div>

        <div className="font-serif text-[36px] leading-[1.25] mb-8 max-w-[560px]">
          What is asking for your attention today?
        </div>

        <div className="border-t border-line pt-7 mb-10">
          {today ? <TodayPractice today={today} /> : <EmptyPractice />}
        </div>

        <RecentConversations conversations={conversations} />
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Run typecheck**

```bash
cd /Volumes/External/soulra && npm run typecheck
```

Expected: no errors. If you see errors about missing imports (`SituationInput`, `Chip`, `listTraditions`, `PracticeArc`, `Tradition`, `FLOW_STEPS`, `PROMPT_CHIPS`), they are expected to be gone since we removed those — make sure the old code is fully replaced, not partially edited.

- [ ] **Step 3: Run lint**

```bash
cd /Volumes/External/soulra && npm run lint
```

Expected: no errors.

- [ ] **Step 4: Start dev server and verify visually**

```bash
cd /Volumes/External/soulra && npm run dev
```

Navigate to `http://localhost:3000/home`. Verify:

1. **With active practice arc:** Page shows date line (e.g. `MONDAY · JUNE 9`), large serif question heading, morning quote + author + analysis, then evening prompt below a rule, then two text-links ("Begin a new conversation →" and "See this week →"), then recent conversations grid.
2. **No textarea appears anywhere on this page.**
3. **No "How Soulra works" step list appears.**
4. **"Begin a new conversation →" link navigates to `/chat`.**
5. **"See this week →" link navigates to `/daily`.**
6. **Without active arc:** Only the heading and "Complete a conversation…" text + "Begin a conversation →" link appear above the rule. Recent conversations still show if any exist.

- [ ] **Step 5: Commit**

```bash
cd /Volumes/External/soulra && git add components/screens/HomeScreen.tsx && git commit -m "feat: redesign Today page as daily anchor, remove chat textarea and how-it-works"
```
