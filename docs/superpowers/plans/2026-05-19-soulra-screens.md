# Soulra — Plan B: Full Screen Implementation (All 6 Screens)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
> **Prerequisite:** Plan A (Foundation) must be complete. All UI primitives and Sidebar component must exist.

**Goal:** Implement all 6 wireframe screens (Home, Onboarding, Conversation, Journal, Daily, Crisis) faithfully translated from the wireframe Direction A as the primary UI, pixel-matched to the design tokens.

**Architecture:** Direction A (wise-friend chat) is the primary direction for all screens — it's the most accessible and matches the product's "knowledgeable friend" tone. Each screen is a Next.js Server Component where possible; client components only where interactivity is required (conversation input, journal checkboxes, daily commit buttons). No data fetching yet — all content is static/mock. Plan C (AI engine) wires in real data.

**Tech Stack:** Next.js 14 App Router, TypeScript, Tailwind CSS, components from Plan A.

---

## File Map

```
app/
├── home/page.tsx              # HomeA — dashboard with greeting, teaching, revisit nudge, threads
├── onboarding/page.tsx        # OnboardingA — conversational welcome (3-step flow)
├── chat/page.tsx              # ConversationA — full chat with clarifying pause + tradition cards
├── journal/
│   ├── page.tsx               # JournalA — tagged list + revisit nudge
│   └── empty/page.tsx         # JournalEmptyB — empty state (first open)
├── daily/page.tsx             # DailyA — single morning card
└── crisis/page.tsx            # CrisisA — inline gentle pause (always accessible)
components/
├── screens/
│   ├── HomeScreen.tsx         # HomeA layout
│   ├── ConversationScreen.tsx # ConversationA layout (client)
│   ├── JournalScreen.tsx      # JournalA layout
│   ├── JournalEmptyScreen.tsx # JournalEmptyB layout
│   ├── DailyScreen.tsx        # DailyA layout
│   └── CrisisScreen.tsx       # CrisisA layout
└── conversation/
    ├── TraditionCard.tsx      # single tradition card (expandable)
    ├── ActionPlan.tsx         # "What you can do today" checklist
    ├── CitationBadge.tsx      # inline citation: ↳ Tradition · Book · Chapter
    └── ClarifyingPause.tsx    # the pause moment with chip answers
```

---

### Task 1: Home screen (HomeA)

**Files:**
- Create: `components/screens/HomeScreen.tsx`
- Modify: `app/home/page.tsx`

- [ ] **Step 1: Create `HomeScreen.tsx`**

```tsx
// components/screens/HomeScreen.tsx
import { Sidebar } from "@/components/layout/Sidebar";
import { Button } from "@/components/ui/Button";
import { Chip } from "@/components/ui/Chip";
import { Input } from "@/components/ui/Input";

export function HomeScreen() {
  return (
    <div className="flex h-screen bg-paper overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-auto">

        {/* greeting strip */}
        <div className="px-10 pt-8 pb-6 border-b border-line flex justify-between items-end">
          <div>
            <div className="font-mono text-[10px] text-muted uppercase tracking-widest">
              Friday · good morning
            </div>
            <div className="font-serif text-[36px] leading-tight mt-1.5">
              Welcome back, Mira.
            </div>
            <div className="text-sm text-muted mt-2 max-w-[580px] leading-relaxed">
              You've been working with the question of refusing well.
              Today's lesson is short. Then the day is yours.
            </div>
          </div>
          <Button small>◇ Open journal</Button>
        </div>

        {/* main grid */}
        <div className="px-10 py-6 grid grid-cols-[1.4fr_1fr] gap-5">

          {/* primary CTA */}
          <div className="col-span-2 border border-ink rounded-xl p-6 bg-paper-alt">
            <div className="font-mono text-[10px] text-accent uppercase tracking-widest mb-1.5">
              what is asking for your attention today?
            </div>
            <Input big />
            <div className="flex flex-wrap gap-1.5 mt-3.5 items-center">
              <span className="font-mono text-[10px] text-muted mr-1">or pick up a thread:</span>
              <Chip>refusing well · 4 days in</Chip>
              <Chip>holding loosely</Chip>
              <Chip>+ new thread</Chip>
            </div>
          </div>

          {/* today's teaching */}
          <div className="border border-ink rounded-xl bg-ink text-paper p-6">
            <div className="font-mono text-[10px] text-accent-soft uppercase tracking-widest mb-2">
              today's teaching · 2 min read
            </div>
            <div className="font-serif text-2xl leading-[1.35] italic">
              "You always own the option of having no opinion."
            </div>
            <div className="font-mono text-[10px] text-accent-soft mt-2.5">
              ↳ Marcus Aurelius · Meditations 6.13
            </div>
            <div className="text-sm text-[#cdc6b8] leading-[1.7] mt-3.5">
              Today's only practice: pause for one breath before answering the next request.
            </div>
            <div className="flex gap-2 mt-4">
              <button className="text-xs border border-accent-soft text-accent-soft rounded-full px-3 py-1.5">
                Sit with this →
              </button>
              <button className="text-xs border border-[#3a352d] text-accent-soft rounded-full px-3 py-1.5">
                ◇ Save
              </button>
            </div>
          </div>

          {/* revisit nudge */}
          <div className="border border-ink rounded-xl p-6 bg-paper">
            <div className="font-mono text-[10px] text-accent uppercase tracking-widest mb-2">
              a lesson you kept · 11 days ago
            </div>
            <div className="font-serif text-[19px] leading-[1.4] italic">
              "The yes that secures will resent itself."
            </div>
            <div className="font-mono text-[10px] text-muted mt-2">
              ↳ Bhagavad Gita 2.47
            </div>
            <div className="text-sm text-muted leading-[1.6] mt-3">
              Has it shown up in your week? Mark it lived, or set it down.
            </div>
            <div className="flex gap-2 mt-4">
              <Button small primary>It showed up</Button>
              <Button small>Not yet</Button>
            </div>
          </div>

          {/* recent threads */}
          <div className="col-span-2 border border-line rounded-xl p-5 bg-paper">
            <div className="flex justify-between items-center mb-3">
              <div className="font-mono text-[10px] text-muted uppercase tracking-widest">
                recent conversations
              </div>
              <span className="font-mono text-[10px] text-accent">see all ↗</span>
            </div>
            <div className="grid grid-cols-3 gap-3">
              {[
                ["Saying yes I don't mean", "2 days ago · 3 traditions", "career"],
                ["When grief just sits", "1 wk ago · Sufi · Buddhist", "grief"],
                ["Who am I without the role", "2 wk ago · Vedanta", "identity"],
              ].map(([title, meta, tag]) => (
                <div key={title} className="border border-line rounded-lg p-3 bg-paper-alt">
                  <div className="font-serif text-[15px] leading-[1.35] italic">"{title}"</div>
                  <div className="flex justify-between items-center mt-2.5">
                    <span className="font-mono text-[9px] text-muted">{meta}</span>
                    <Chip className="text-[9px] px-2 py-0.5">{tag}</Chip>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Wire into `app/home/page.tsx`**

```tsx
// app/home/page.tsx
import { HomeScreen } from "@/components/screens/HomeScreen";

export default function HomePage() {
  return <HomeScreen />;
}
```

- [ ] **Step 3: Commit**

```bash
git add components/screens/HomeScreen.tsx app/home/page.tsx
git commit -m "feat: implement Home screen (Direction A)"
```

---

### Task 2: Conversation sub-components

**Files:**
- Create: `components/conversation/CitationBadge.tsx`
- Create: `components/conversation/ClarifyingPause.tsx`
- Create: `components/conversation/TraditionCard.tsx`
- Create: `components/conversation/ActionPlan.tsx`

- [ ] **Step 1: Create `CitationBadge.tsx`**

```tsx
// components/conversation/CitationBadge.tsx
interface CitationBadgeProps {
  tradition: string;
  book: string;
  chapter: string;
}

export function CitationBadge({ tradition, book, chapter }: CitationBadgeProps) {
  return (
    <div className="flex items-center gap-2 font-mono text-[10px] text-accent pt-2.5 border-t border-dashed border-line mt-3.5">
      <span>↳</span>
      <span>{tradition} · {book} · {chapter}</span>
      <span className="ml-auto text-muted cursor-pointer">tap to read original ↗</span>
    </div>
  );
}
```

- [ ] **Step 2: Create `ClarifyingPause.tsx`**

```tsx
// components/conversation/ClarifyingPause.tsx
"use client";
import { useState } from "react";
import { Chip } from "@/components/ui/Chip";

interface ClarifyingPauseProps {
  question: string;
  options: string[];
  onSelect?: (option: string) => void;
}

export function ClarifyingPause({ question, options, onSelect }: ClarifyingPauseProps) {
  const [selected, setSelected] = useState<string | null>(null);

  function handleSelect(opt: string) {
    setSelected(opt);
    onSelect?.(opt);
  }

  return (
    <div className="flex gap-3.5">
      <div className="w-8 h-8 rounded-full border border-ink flex items-center justify-center font-serif text-sm flex-shrink-0">
        S
      </div>
      <div className="flex-1">
        <div className="font-mono text-[10px] text-muted uppercase tracking-wide mb-1.5">
          Soulra · pausing to understand
        </div>
        <div className="font-serif text-[19px] leading-[1.5] italic">{question}</div>
        <div className="flex flex-wrap gap-2 mt-3.5">
          {options.map(opt => (
            <Chip key={opt} active={selected === opt} onClick={() => handleSelect(opt)}>
              {opt}
            </Chip>
          ))}
        </div>
        <div className="font-mono text-[10px] text-muted mt-2">…or just type a longer answer</div>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Make Chip accept onClick**

Modify `components/ui/Chip.tsx` to accept `onClick`:

```tsx
// components/ui/Chip.tsx
interface ChipProps {
  children: React.ReactNode;
  active?: boolean;
  className?: string;
  onClick?: () => void;
}

export function Chip({ children, active, className, onClick }: ChipProps) {
  return (
    <span
      onClick={onClick}
      className={[
        "inline-flex items-center px-3 py-1 rounded-full text-xs font-sans",
        "border transition-colors",
        active ? "border-ink bg-ink text-paper" : "border-line bg-transparent text-ink",
        onClick ? "cursor-pointer" : "",
        className,
      ].filter(Boolean).join(" ")}
    >
      {children}
    </span>
  );
}
```

- [ ] **Step 4: Create `TraditionCard.tsx`**

```tsx
// components/conversation/TraditionCard.tsx
"use client";
import { useState } from "react";
import { CitationBadge } from "./CitationBadge";

interface TraditionCardProps {
  index: number;
  total: number;
  tradition: string;
  author: string;
  quote: string;
  explanation: string;
  citationBook: string;
  citationChapter: string;
  initiallyExpanded?: boolean;
}

export function TraditionCard({
  index, total, tradition, author, quote, explanation,
  citationBook, citationChapter, initiallyExpanded = false,
}: TraditionCardProps) {
  const [expanded, setExpanded] = useState(initiallyExpanded);

  if (!expanded) {
    return (
      <div
        className="border border-line rounded-xl p-4 bg-paper-alt cursor-pointer"
        onClick={() => setExpanded(true)}
      >
        <div className="flex items-center justify-between">
          <div>
            <div className="font-mono text-[10px] text-accent uppercase tracking-widest mb-1">
              {tradition} · {author}
            </div>
            <div className="font-serif text-base italic">
              {quote.slice(0, 60)}…
            </div>
          </div>
          <span className="font-mono text-[11px] text-muted ml-4 flex-shrink-0">
            {index} of {total} · expand ↓
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className="border border-ink rounded-xl p-5 bg-paper">
      <div className="flex items-center justify-between mb-2">
        <div className="font-mono text-[10px] text-accent uppercase tracking-widest">
          {tradition} · {author}
        </div>
        <span className="font-mono text-[11px] text-muted">{index} of {total}</span>
      </div>
      <div className="font-serif text-[22px] leading-[1.35] italic">{quote}</div>
      <div className="text-sm leading-[1.7] mt-3 text-muted">{explanation}</div>
      <CitationBadge tradition={tradition} book={citationBook} chapter={citationChapter} />
    </div>
  );
}
```

- [ ] **Step 5: Create `ActionPlan.tsx`**

```tsx
// components/conversation/ActionPlan.tsx
"use client";
import { useState } from "react";

interface ActionStep {
  number: string;
  title: string;
  body: string;
}

interface ActionPlanProps {
  steps: ActionStep[];
  onSaveToJournal?: () => void;
}

export function ActionPlan({ steps, onSaveToJournal }: ActionPlanProps) {
  const [committed, setCommitted] = useState<Set<number>>(new Set());

  function toggle(i: number) {
    setCommitted(prev => {
      const next = new Set(prev);
      next.has(i) ? next.delete(i) : next.add(i);
      return next;
    });
  }

  return (
    <div className="border border-ink rounded-xl bg-ink text-paper p-6 mt-2">
      <div className="font-mono text-[10px] text-accent-soft uppercase tracking-widest mb-1">
        What you can do today
      </div>
      <div className="font-serif text-[22px] font-medium mb-5">
        Three steps. Pick the one you'll try.
      </div>

      {steps.map((step, i) => (
        <div
          key={i}
          className={["flex gap-3.5 py-3", i > 0 ? "border-t border-[#3a352d]" : ""].join(" ")}
        >
          <button
            onClick={() => toggle(i)}
            className="w-[22px] h-[22px] border border-accent-soft rounded flex-shrink-0 mt-0.5 flex items-center justify-center text-xs text-accent-soft"
            style={{ background: committed.has(i) ? "rgba(216,200,172,0.2)" : "transparent" }}
          >
            {committed.has(i) ? "✓" : ""}
          </button>
          <div className="flex-1">
            <div className="font-mono text-[10px] text-accent-soft tracking-wide">{step.number}</div>
            <div className="text-sm font-medium mt-0.5">{step.title}</div>
            <div className="text-[13px] text-[#cdc6b8] leading-[1.6] mt-1">{step.body}</div>
          </div>
        </div>
      ))}

      <div className="flex gap-2 mt-4 pt-3.5 border-t border-[#3a352d]">
        <button className="text-xs border border-accent-soft text-accent-soft rounded-full px-3 py-1.5">
          I'll try one of these
        </button>
        <button className="text-xs border border-[#3a352d] text-accent-soft rounded-full px-3 py-1.5">
          Suggest different steps
        </button>
        <span className="flex-1" />
        <button onClick={onSaveToJournal} className="text-xs border border-accent-soft text-accent-soft rounded-full px-3 py-1.5">
          ◇ Save to journal
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 6: Commit**

```bash
git add components/conversation/ components/ui/Chip.tsx
git commit -m "feat: add conversation sub-components (CitationBadge, ClarifyingPause, TraditionCard, ActionPlan)"
```

---

### Task 3: Conversation screen (ConversationA)

**Files:**
- Create: `components/screens/ConversationScreen.tsx`
- Modify: `app/chat/page.tsx`

- [ ] **Step 1: Create `ConversationScreen.tsx`**

```tsx
// components/screens/ConversationScreen.tsx
"use client";
import { Sidebar } from "@/components/layout/Sidebar";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { ClarifyingPause } from "@/components/conversation/ClarifyingPause";
import { TraditionCard } from "@/components/conversation/TraditionCard";
import { ActionPlan } from "@/components/conversation/ActionPlan";

const TRADITION_CARDS = [
  {
    index: 1, total: 3, tradition: "Stoic", author: "Marcus Aurelius",
    quote: '"You always own the option of having no opinion. There is never any need to get worked up or to trouble your soul about things you can't control."',
    explanation: "The Stoic move here is to notice that the request comes from outside but the yes comes from within. The pressure feels external; the agreement is yours. That distinction is where freedom begins.",
    citationBook: "Meditations", citationChapter: "Book 6, 13 — trans. Hays (2002)",
    initiallyExpanded: true,
  },
  {
    index: 2, total: 3, tradition: "Vedanta", author: "Bhagavad Gita",
    quote: '"On action without attachment to its fruit…"',
    explanation: "What if the yes is a way of trying to secure something — approval, belonging, identity? Krishna's teaching is that any work done to secure those things will resent itself.",
    citationBook: "Bhagavad Gita", citationChapter: "Chapter 2, Verse 47 — trans. Easwaran (2007)",
    initiallyExpanded: false,
  },
  {
    index: 3, total: 3, tradition: "Buddhist", author: "Pema Chödrön",
    quote: '"The yes beneath the yes — a closer look at the resistance itself…"',
    explanation: "What if the resistance is the teacher? Staying close to discomfort rather than running from it reveals what the yes is really protecting.",
    citationBook: "When Things Fall Apart", citationChapter: "Ch. 9",
    initiallyExpanded: false,
  },
];

const ACTION_STEPS = [
  { number: "01", title: "Notice the moment of yes", body: "When the next request arrives, pause for the length of one breath before answering. That is the only practice today." },
  { number: "02", title: "Name what you actually want", body: "Write one sentence: 'What I would say if there were no consequence is ___.' Don't act on it. Just see it." },
  { number: "03", title: "Say a small, true no", body: "Decline one small, low-stakes request this week. Keep it warm and brief: 'Not this one — thank you for asking.'" },
];

export function ConversationScreen() {
  return (
    <div className="flex h-screen bg-paper overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">

        {/* top bar */}
        <div className="px-9 py-4 border-b border-line flex items-center justify-between">
          <div>
            <div className="font-serif text-base font-medium">Saying yes I don't mean</div>
            <div className="font-mono text-[10px] text-muted mt-0.5">
              started 2 min ago · 3 traditions consulted
            </div>
          </div>
          <div className="flex gap-2">
            <Button small>◇ Save to journal</Button>
            <Button small>⋯</Button>
          </div>
        </div>

        {/* thread */}
        <div className="flex-1 overflow-auto px-9 py-8 flex flex-col gap-7 max-w-[820px] self-center w-full">

          {/* user message */}
          <div className="self-end max-w-[520px] p-4 bg-paper-alt border border-line text-sm leading-relaxed"
               style={{ borderRadius: "14px 14px 2px 14px" }}>
            I keep saying yes to projects I don't really want to do, and then resenting myself for it.
            I don't know how to stop.
          </div>

          {/* clarifying pause */}
          <ClarifyingPause
            question="Before I draw on the traditions — is this most about the work itself, the people you're saying yes to, or something inside you that finds it hard to refuse?"
            options={["The work", "The people", "Something inside me", "It's all three"]}
          />

          {/* opening reflection */}
          <div className="ml-[46px] text-sm leading-[1.7] max-w-[640px]">
            Thank you. What you're describing — the inability to refuse — has been examined carefully
            across several traditions. Here are three perspectives, each rooted in its own lineage.
            They don't say the same thing, and that is the point.
          </div>

          {/* tradition cards */}
          <div className="ml-[46px] flex flex-col gap-4">
            {TRADITION_CARDS.map(card => (
              <TraditionCard key={card.index} {...card} />
            ))}
          </div>

          {/* action plan */}
          <div className="ml-[46px]">
            <ActionPlan steps={ACTION_STEPS} />
          </div>

          {/* response footer */}
          <div className="ml-[46px] flex justify-between items-center font-mono text-[10px] text-muted pt-1">
            <span>3 sources · 0 paraphrases · grounded response</span>
            <span>was this grounded? · 👍 · 👎</span>
          </div>
        </div>

        {/* input bar */}
        <div className="px-9 py-4 border-t border-line">
          <div className="max-w-[820px] mx-auto">
            <Input placeholder="Reply, or ask a follow-up…" />
          </div>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Wire into `app/chat/page.tsx`**

```tsx
// app/chat/page.tsx
import { ConversationScreen } from "@/components/screens/ConversationScreen";

export default function ChatPage() {
  return <ConversationScreen />;
}
```

- [ ] **Step 3: Commit**

```bash
git add components/screens/ConversationScreen.tsx app/chat/page.tsx
git commit -m "feat: implement Conversation screen (Direction A) with TraditionCards and ActionPlan"
```

---

### Task 4: Journal screen (JournalA + empty state)

**Files:**
- Create: `components/screens/JournalScreen.tsx`
- Create: `components/screens/JournalEmptyScreen.tsx`
- Modify: `app/journal/page.tsx`
- Create: `app/journal/empty/page.tsx`

- [ ] **Step 1: Create `JournalScreen.tsx`**

```tsx
// components/screens/JournalScreen.tsx
import { Sidebar } from "@/components/layout/Sidebar";
import { Button } from "@/components/ui/Button";
import { Chip } from "@/components/ui/Chip";

const JOURNAL_ENTRIES = [
  { date: "Apr 28", title: "Three small things to refuse warmly.", source: "Stoic · Marcus Aurelius · Meditations 6.13", tags: ["career", "practice"], applied: true },
  { date: "Apr 21", title: "Action without attachment to the fruit.", source: "Vedanta · Bhagavad Gita 2.47", tags: ["career"], applied: false },
  { date: "Apr 18", title: "What if the resistance itself is the teacher?", source: "Buddhist · Pema Chödrön · When Things Fall Apart", tags: ["identity"], applied: true },
  { date: "Apr 11", title: "On grief: a guest you stop trying to evict.", source: "Sufi · Rumi · The Guest House", tags: ["grief"], applied: false },
  { date: "Apr 04", title: "The disquiet that returns is asking to be heard.", source: "Christian mystics · Thomas à Kempis", tags: ["identity"], applied: false },
];

const TAGS = [
  ["all", 12, true], ["career", 5, false], ["relationships", 3, false],
  ["grief", 1, false], ["identity", 2, false], ["practice", 4, false],
] as const;

export function JournalScreen() {
  return (
    <div className="flex h-screen bg-paper overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">

        {/* header */}
        <div className="px-10 pt-7 pb-5 border-b border-line flex items-end justify-between">
          <div>
            <div className="font-mono text-[10px] text-muted uppercase tracking-widest">your journal</div>
            <div className="font-serif text-[36px] leading-tight mt-1">Wisdom you've kept</div>
            <div className="text-sm text-muted mt-1.5">
              12 lessons · 3 applied this month · last revisit 4 days ago
            </div>
          </div>
          <div className="flex gap-2">
            <Button small>↗ Export PDF</Button>
            <Button small>+ Add a private note</Button>
          </div>
        </div>

        <div className="flex flex-1 overflow-hidden">
          {/* tag rail */}
          <div className="w-[220px] border-r border-line p-6 flex flex-col gap-5 flex-shrink-0">
            <div>
              <div className="font-mono text-[10px] text-muted uppercase tracking-widest mb-2.5">tags</div>
              {TAGS.map(([name, count, active]) => (
                <div key={name} className={["flex justify-between text-sm py-1", active ? "font-medium text-ink" : "text-muted"].join(" ")}>
                  <span>{name}</span>
                  <span className="font-mono text-[11px]">{count}</span>
                </div>
              ))}
            </div>
            <div>
              <div className="font-mono text-[10px] text-muted uppercase tracking-widest mb-2.5">traditions</div>
              {[["Stoic", 5], ["Vedanta", 4], ["Buddhist", 3]].map(([t, c]) => (
                <div key={t} className="flex justify-between text-sm text-muted py-1">
                  <span>{t}</span><span className="font-mono text-[11px]">{c}</span>
                </div>
              ))}
            </div>
          </div>

          {/* main list */}
          <div className="flex-1 overflow-auto px-9 py-6">
            {/* revisit nudge */}
            <div className="border border-ink rounded-xl p-6 flex gap-4 bg-paper-alt mb-6">
              <div className="flex-1">
                <div className="font-mono text-[10px] text-accent uppercase tracking-widest mb-1">
                  a lesson worth revisiting
                </div>
                <div className="font-serif text-[22px] leading-[1.35] italic">
                  "You always own the option of having no opinion."
                </div>
                <div className="font-mono text-[11px] text-muted mt-2">
                  saved 11 days ago · Stoic · Meditations 6.13
                </div>
              </div>
              <div className="flex flex-col gap-2 items-end">
                <Button small primary>Open</Button>
                <span className="font-mono text-[10px] text-muted">has it shown up?</span>
              </div>
            </div>

            {/* entries */}
            <div className="border border-line rounded-xl overflow-hidden">
              {JOURNAL_ENTRIES.map((entry, i) => (
                <div key={i} className={["flex items-start gap-4 p-5", i > 0 ? "border-t border-line-soft" : ""].join(" ")}>
                  <span className={[
                    "w-[18px] h-[18px] border border-ink rounded flex-shrink-0 mt-1 flex items-center justify-center text-[11px]",
                    entry.applied ? "bg-ink text-paper" : "bg-transparent",
                  ].join(" ")}>
                    {entry.applied ? "✓" : ""}
                  </span>
                  <div className="flex-1">
                    <div className="font-serif text-[17px] leading-[1.4]">{entry.title}</div>
                    <div className="font-mono text-[10px] text-accent mt-1.5 tracking-[0.3px]">↳ {entry.source}</div>
                    <div className="flex gap-1.5 mt-2">
                      {entry.tags.map(tag => (
                        <Chip key={tag} className="text-[10px] px-2 py-0.5">{tag}</Chip>
                      ))}
                    </div>
                  </div>
                  <div className="font-mono text-[10px] text-muted mt-1 flex-shrink-0">{entry.date}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Create `JournalEmptyScreen.tsx`**

```tsx
// components/screens/JournalEmptyScreen.tsx
import { Sidebar } from "@/components/layout/Sidebar";
import { Button } from "@/components/ui/Button";
import { Squiggle } from "@/components/ui/Squiggle";

export function JournalEmptyScreen() {
  return (
    <div className="flex h-screen bg-paper overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-auto px-15">

        <div className="pt-15 pb-8 border-b border-line-soft">
          <div className="font-mono text-[10px] text-muted uppercase tracking-widest">your journal</div>
          <div className="font-serif text-[44px] leading-tight mt-2 italic">
            A place for wisdom<br />that has met you.
          </div>
          <Squiggle width={140} className="mt-4" />
        </div>

        <div className="grid grid-cols-2 gap-15 pt-10 pb-15">
          <div>
            <p className="text-[15px] leading-[1.7] text-ink max-w-[460px]">
              Most chat apps treat saved messages like a graveyard. This isn't that.
            </p>
            <p className="text-[15px] leading-[1.7] text-ink max-w-[460px] mt-4">
              Your journal is the small library of teachings that, for whatever reason, stayed with you.
              A few weeks from now, Soulra will quietly bring one back — not to remind you of an answer,
              but to ask whether it has shown up.
            </p>
            <div className="flex flex-col gap-3.5 mt-8">
              {[
                ["◇", "Save anything that resonates", "Tap the bookmark on any lesson."],
                ["◯", "Tag by season of life", "Career, grief, identity — your own labels work too."],
                ["⤴", "Mark when it shows up", "The lesson lived is worth more than the lesson read."],
              ].map(([icon, title, body]) => (
                <div key={title} className="flex gap-3.5 items-start">
                  <span className="font-mono text-base text-accent w-[18px] mt-0.5">{icon}</span>
                  <div>
                    <div className="font-serif text-[17px] leading-tight">{title}</div>
                    <div className="text-sm text-muted mt-0.5">{body}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div>
            <div className="font-mono text-[10px] text-muted uppercase tracking-widest mb-3.5">
              a starting place — your first saved lesson
            </div>
            <div className="border border-ink rounded-xl bg-paper-alt p-6">
              <div className="font-mono text-[10px] text-accent uppercase tracking-widest mb-2">
                Stoic · Epictetus
              </div>
              <div className="font-serif text-[22px] leading-[1.4] italic">
                "It is not what happens to you, but how you react to it that matters."
              </div>
              <div className="text-sm text-muted mt-3.5 leading-[1.6]">
                We've placed one teaching here to begin. You don't have to keep it.
                When something resonates more, it can take its place.
              </div>
              <div className="flex gap-2.5 mt-5 pt-3.5 border-t border-dashed border-line items-center">
                <Button small primary>Keep this one</Button>
                <Button small>Choose another →</Button>
                <span className="flex-1" />
                <span className="font-mono text-[10px] text-muted">Discourses · 1.1.7</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Wire pages**

```tsx
// app/journal/page.tsx
import { JournalScreen } from "@/components/screens/JournalScreen";
export default function JournalPage() { return <JournalScreen />; }
```

```tsx
// app/journal/empty/page.tsx
import { JournalEmptyScreen } from "@/components/screens/JournalEmptyScreen";
export default function JournalEmptyPage() { return <JournalEmptyScreen />; }
```

- [ ] **Step 4: Commit**

```bash
git add components/screens/JournalScreen.tsx components/screens/JournalEmptyScreen.tsx app/journal/
git commit -m "feat: implement Journal screen and empty state (Direction A + B)"
```

---

### Task 5: Daily practice screen (DailyA)

**Files:**
- Create: `components/screens/DailyScreen.tsx`
- Modify: `app/daily/page.tsx`

- [ ] **Step 1: Create `DailyScreen.tsx`**

```tsx
// components/screens/DailyScreen.tsx
import { Sidebar } from "@/components/layout/Sidebar";
import { Button } from "@/components/ui/Button";

export function DailyScreen() {
  return (
    <div className="flex h-screen bg-paper overflow-hidden">
      <Sidebar />
      <div className="flex-1 px-20 py-15 overflow-auto flex flex-col gap-7">

        <div>
          <div className="font-mono text-[10px] text-muted uppercase tracking-widest">
            Friday · morning
          </div>
          <div className="font-serif text-[36px] leading-tight mt-1.5">Good morning, Mira.</div>
          <div className="text-sm text-muted mt-2 max-w-[580px] leading-relaxed">
            Today's lesson is drawn from the situation you brought last week — the difficulty of refusing.
            We'll sit with one teaching, and an evening prompt will arrive at 8pm.
          </div>
        </div>

        <div className="border border-ink rounded-xl bg-paper-alt p-8 max-w-[760px]">
          <div className="flex justify-between items-center">
            <div className="font-mono text-[10px] text-accent uppercase tracking-widest">
              Stoic · Marcus Aurelius · Meditations 6.13
            </div>
            <span className="font-mono text-[10px] text-muted">day 4 of this thread</span>
          </div>

          <div className="font-serif text-[32px] leading-[1.3] italic mt-4">
            "You always own the option of having no opinion."
          </div>

          <div className="text-sm leading-[1.75] mt-4 max-w-[560px]">
            The Stoics believed the inner citadel — the part of us that decides — is never actually under siege
            from outside. Today, watch for the moment when a request arrives. Notice the small space between
            the request and your answer. That space is the practice.
          </div>

          <div className="mt-6 p-4 border border-dashed border-line rounded-lg">
            <div className="font-mono text-[10px] text-muted uppercase tracking-wide mb-1">
              today's only practice
            </div>
            <div className="text-[15px] font-medium">
              Pause for one breath before answering the next request you receive.
            </div>
          </div>

          <div className="flex gap-2.5 mt-5">
            <Button small primary>I'll carry this today</Button>
            <Button small>Read the full passage ↗</Button>
            <span className="flex-1" />
            <Button small>◇ Save</Button>
          </div>
        </div>

        <div>
          <div className="font-mono text-[10px] text-muted uppercase tracking-widest mt-4">
            tonight at 8pm
          </div>
          <div className="font-serif text-[18px] text-muted italic mt-1">
            "Did the space appear? What did you find in it?"
          </div>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Wire page**

```tsx
// app/daily/page.tsx
import { DailyScreen } from "@/components/screens/DailyScreen";
export default function DailyPage() { return <DailyScreen />; }
```

- [ ] **Step 3: Commit**

```bash
git add components/screens/DailyScreen.tsx app/daily/page.tsx
git commit -m "feat: implement Daily practice screen (Direction A)"
```

---

### Task 6: Crisis fallback screen (CrisisA)

**Files:**
- Create: `components/screens/CrisisScreen.tsx`
- Create: `app/crisis/page.tsx`

- [ ] **Step 1: Create `CrisisScreen.tsx`**

```tsx
// components/screens/CrisisScreen.tsx
import { Sidebar } from "@/components/layout/Sidebar";
import { Button } from "@/components/ui/Button";

const HELP_LINES = [
  { number: "988", description: "Suicide & Crisis Lifeline · US · call or text" },
  { number: "741741", description: "Crisis Text Line · text HOME · US, UK, Ireland, Canada" },
  { number: "findahelpline.com", description: "find a free line in your country ↗" },
];

export function CrisisScreen() {
  return (
    <div className="flex h-screen bg-paper overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">

        <div className="px-9 py-4 border-b border-line">
          <div className="font-serif text-base font-medium">A heavy day</div>
        </div>

        <div className="flex-1 px-9 py-8 overflow-auto flex flex-col gap-6 max-w-[760px] self-center w-full">

          {/* user message */}
          <div className="self-end max-w-[540px] p-4 bg-paper-alt border border-line text-sm leading-relaxed"
               style={{ borderRadius: "14px 14px 2px 14px" }}>
            I'm so tired of being here. I don't know if I want to keep going.
          </div>

          {/* Soulra response — no philosophy */}
          <div className="flex gap-3.5">
            <div className="w-8 h-8 rounded-full border border-ink flex items-center justify-center font-serif text-sm flex-shrink-0">
              S
            </div>
            <div className="flex-1">
              <div className="font-serif text-[22px] leading-[1.5]">
                I'm here. Thank you for telling me — and please stay with me a moment
                before I say anything more.
              </div>
              <div className="text-sm leading-[1.7] mt-3.5">
                What you wrote is heavy, and I want to make sure you have more than my words right now.
                I'm an AI companion, not a substitute for a person who can be with you tonight.
              </div>
            </div>
          </div>

          {/* care card */}
          <div className="ml-[46px] border border-ink rounded-xl bg-paper-alt p-6">
            <div className="font-mono text-[10px] text-accent uppercase tracking-widest mb-2">
              a person to talk to, right now
            </div>
            <div className="font-serif text-[22px] leading-[1.4]">
              These lines are answered 24/7 by people trained to listen.
            </div>

            <div className="flex flex-col gap-2.5 mt-4">
              {HELP_LINES.map(line => (
                <div key={line.number} className="flex items-center gap-3.5 p-3 border border-line rounded-lg bg-paper">
                  <span className="font-serif text-[22px] font-medium min-w-[140px]">{line.number}</span>
                  <span className="text-sm text-muted">{line.description}</span>
                  <span className="ml-auto font-mono text-[11px] text-accent">open ↗</span>
                </div>
              ))}
            </div>

            <div className="mt-4 p-3 border border-dashed border-line rounded text-sm leading-[1.6] text-muted">
              If you're in immediate danger, please call your local emergency number.
              I'll wait here. Coming back later is welcome.
            </div>
          </div>

          {/* still here */}
          <div className="ml-[46px]">
            <div className="text-sm leading-[1.7] max-w-[540px]">
              When you're ready — and only if you'd like — I can stay with you here, without
              advice or philosophy. We can just talk.
            </div>
            <div className="flex gap-2 mt-3.5">
              <Button small>Just stay with me</Button>
              <Button small>I'll reach out for help first</Button>
            </div>
          </div>
        </div>

        {/* input paused */}
        <div className="px-9 py-4 border-t border-line bg-paper-alt">
          <div className="max-w-[760px] mx-auto font-mono text-[11px] text-muted text-center">
            the action plan and source citations are paused for this conversation
          </div>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Create `app/crisis/page.tsx`**

```tsx
// app/crisis/page.tsx
import { CrisisScreen } from "@/components/screens/CrisisScreen";
export default function CrisisPage() { return <CrisisScreen />; }
```

- [ ] **Step 3: Build and type check**

```bash
npm run build 2>&1 | tail -30
```

Expected: build completes with no TypeScript errors.

- [ ] **Step 4: Commit**

```bash
git add components/screens/CrisisScreen.tsx app/crisis/
git commit -m "feat: implement Crisis fallback screen (Direction A)"
```

---

## Self-Review

**Spec coverage:**
- ✅ Home screen: greeting, teaching card, revisit nudge, recent threads, primary input
- ✅ Conversation screen: user message, clarifying pause with chips, 3 tradition cards (1 expanded, 2 collapsed), opening reflection, action plan checklist, response footer
- ✅ Journal: tag rail, revisit nudge, entries with applied checkmarks
- ✅ Journal empty state: teaches what the journal is for, seed lesson
- ✅ Daily: morning teaching card, practice instruction, evening reflection preview
- ✅ Crisis: no philosophy, warm response, 3 help lines prominently, "I'll wait here"
- ✅ Citations appear in TraditionCard (CitationBadge) and journal entries
- ✅ Action plan has commit checkboxes
- ✅ Crisis pauses the input bar

**Placeholder scan:** None.

**Type consistency:** All component props typed. TraditionCard props match usage in ConversationScreen. ActionStep interface consistent between definition and usage.
