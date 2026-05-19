# Soulra — Plan A: Foundation (Scaffold + Design System)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Scaffold a Next.js 14 app with the Soulra design system (tokens, primitives, sidebar, layout) faithfully translated from the wireframes, with a working multi-page shell.

**Architecture:** Next.js 14 App Router + TypeScript. Design tokens extracted from `wireframe-primitives.jsx` into a `lib/tokens.ts` file used across all components. Tailwind CSS for layout; inline styles only when Tailwind can't express the exact value. All fonts loaded via `next/font/google`.

**Tech Stack:** Next.js 14, TypeScript, Tailwind CSS, shadcn/ui (base only), Cormorant Garamond + Inter + JetBrains Mono + Caveat fonts.

---

## Design Token Reference (from wireframes)

```ts
// lib/tokens.ts — copy these exactly
ink:        "#1d1b18"   // near-black warm
paper:      "#f7f4ee"   // warm off-white
paperAlt:   "#efeae0"
line:       "#cdc6b8"
lineSoft:   "#e3ddd0"
muted:      "#7d7568"
accent:     "#7a5c3e"   // muted ochre/wisdom
accentSoft: "#d8c8ac"
danger:     "#8a4a3c"
```

Fonts:
- `serif`: Cormorant Garamond (400, 500, 600, italic variants)
- `sans`: Inter (400, 500, 600)
- `mono`: JetBrains Mono (400, 500)
- `handwritten`: Caveat (400, 500) — annotation notes only

---

## File Map

```
soulra/
├── app/
│   ├── layout.tsx              # root layout: fonts, metadata, bg color
│   ├── page.tsx                # redirect to /home
│   ├── home/page.tsx           # Home/Today screen (Direction A)
│   ├── chat/page.tsx           # Conversation screen (Direction A)
│   ├── journal/page.tsx        # Journal screen (Direction A + empty state)
│   ├── daily/page.tsx          # Daily practice screen (Direction A)
│   └── globals.css             # Tailwind base + font CSS vars
├── components/
│   ├── ui/
│   │   ├── Wordmark.tsx        # WfWordmark
│   │   ├── Chip.tsx            # WfChip
│   │   ├── Button.tsx          # WfBtn
│   │   ├── Input.tsx           # WfInput
│   │   ├── Squiggle.tsx        # WfSquiggle
│   │   └── SectionHead.tsx     # WfSectionHead
│   └── layout/
│       └── Sidebar.tsx         # WfSidebar (nav with active state)
├── lib/
│   └── tokens.ts               # design tokens as typed constants
└── tailwind.config.ts          # extend with token colors + fonts
```

---

### Task 1: Initialize Next.js project

**Files:**
- Create: `package.json`, `tsconfig.json`, `tailwind.config.ts`, `postcss.config.js`, `next.config.ts`

- [ ] **Step 1: Run create-next-app**

```bash
cd /Volumes/External/soulra
npx create-next-app@latest . \
  --typescript \
  --tailwind \
  --eslint \
  --app \
  --no-src-dir \
  --import-alias "@/*" \
  --yes
```

Expected: project scaffolded, `package.json`, `app/`, `tailwind.config.ts` created.

- [ ] **Step 2: Verify it runs**

```bash
npm run dev &
sleep 4
curl -s http://localhost:3000 | head -20
kill %1
```

Expected: HTML returned (Next.js default page).

- [ ] **Step 3: Remove boilerplate**

Delete `app/page.tsx` content and replace with a simple redirect:

```tsx
// app/page.tsx
import { redirect } from "next/navigation";
export default function Root() {
  redirect("/home");
}
```

Delete `app/globals.css` Tailwind directives section below the `@tailwind` lines (remove the default CSS variables block).

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "feat: initialize Next.js 14 app with TypeScript + Tailwind"
```

---

### Task 2: Design tokens + Tailwind config

**Files:**
- Create: `lib/tokens.ts`
- Modify: `tailwind.config.ts`
- Modify: `app/globals.css`

- [ ] **Step 1: Create `lib/tokens.ts`**

```ts
// lib/tokens.ts
export const tokens = {
  ink:        "#1d1b18",
  paper:      "#f7f4ee",
  paperAlt:   "#efeae0",
  line:       "#cdc6b8",
  lineSoft:   "#e3ddd0",
  muted:      "#7d7568",
  accent:     "#7a5c3e",
  accentSoft: "#d8c8ac",
  danger:     "#8a4a3c",
} as const;

export type Token = keyof typeof tokens;
```

- [ ] **Step 2: Extend Tailwind config**

Replace the `theme.extend` section in `tailwind.config.ts`:

```ts
theme: {
  extend: {
    colors: {
      ink:        "#1d1b18",
      paper:      "#f7f4ee",
      "paper-alt":"#efeae0",
      line:       "#cdc6b8",
      "line-soft":"#e3ddd0",
      muted:      "#7d7568",
      accent:     "#7a5c3e",
      "accent-soft":"#d8c8ac",
      danger:     "#8a4a3c",
    },
    fontFamily: {
      serif: ["var(--font-cormorant)", "Georgia", "serif"],
      sans:  ["var(--font-inter)", "system-ui", "sans-serif"],
      mono:  ["var(--font-jetbrains)", "ui-monospace", "monospace"],
      hand:  ["var(--font-caveat)", "cursive"],
    },
  },
},
```

- [ ] **Step 3: Add font CSS variables in `app/globals.css`**

```css
/* app/globals.css */
@tailwind base;
@tailwind components;
@tailwind utilities;

html, body {
  background-color: #ece6d8;
  color: #1d1b18;
}
```

(Fonts will be loaded via `next/font/google` in layout.tsx — CSS vars set there.)

- [ ] **Step 4: Commit**

```bash
git add lib/tokens.ts tailwind.config.ts app/globals.css
git commit -m "feat: add design tokens and Tailwind color/font extensions"
```

---

### Task 3: Root layout with fonts

**Files:**
- Modify: `app/layout.tsx`

- [ ] **Step 1: Write `app/layout.tsx`**

```tsx
// app/layout.tsx
import type { Metadata } from "next";
import { Cormorant_Garamond, Inter, JetBrains_Mono, Caveat } from "next/font/google";
import "./globals.css";

const cormorant = Cormorant_Garamond({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  style: ["normal", "italic"],
  variable: "--font-cormorant",
});

const inter = Inter({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-inter",
});

const jetbrains = JetBrains_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-jetbrains",
});

const caveat = Caveat({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-caveat",
});

export const metadata: Metadata = {
  title: "Soulra — Ancient Wisdom. Real Life. Right Now.",
  description: "An AI wisdom companion that translates the world's great spiritual literature into actionable, personalized guidance.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${cormorant.variable} ${inter.variable} ${jetbrains.variable} ${caveat.variable}`}>
      <body className="font-sans antialiased">{children}</body>
    </html>
  );
}
```

- [ ] **Step 2: Run dev and verify fonts load**

```bash
npm run dev &
sleep 4
curl -s http://localhost:3000/home 2>&1 | head -5
kill %1
```

Expected: no font import errors in terminal.

- [ ] **Step 3: Commit**

```bash
git add app/layout.tsx
git commit -m "feat: load Cormorant Garamond, Inter, JetBrains Mono, Caveat via next/font"
```

---

### Task 4: UI primitives — Wordmark, Chip, Button

**Files:**
- Create: `components/ui/Wordmark.tsx`
- Create: `components/ui/Chip.tsx`
- Create: `components/ui/Button.tsx`

- [ ] **Step 1: Create `Wordmark.tsx`**

```tsx
// components/ui/Wordmark.tsx
interface WordmarkProps { size?: number }

export function Wordmark({ size = 22 }: WordmarkProps) {
  return (
    <span
      className="font-serif font-medium uppercase tracking-widest"
      style={{ fontSize: size, letterSpacing: size * 0.15 }}
    >
      Soulra
    </span>
  );
}
```

- [ ] **Step 2: Create `Chip.tsx`**

```tsx
// components/ui/Chip.tsx
interface ChipProps {
  children: React.ReactNode;
  active?: boolean;
  className?: string;
}

export function Chip({ children, active, className }: ChipProps) {
  return (
    <span
      className={[
        "inline-flex items-center px-3 py-1 rounded-full text-xs font-sans",
        "border transition-colors",
        active
          ? "border-ink bg-ink text-paper"
          : "border-line bg-transparent text-ink",
        className,
      ].filter(Boolean).join(" ")}
    >
      {children}
    </span>
  );
}
```

- [ ] **Step 3: Create `Button.tsx`**

```tsx
// components/ui/Button.tsx
interface ButtonProps {
  children: React.ReactNode;
  primary?: boolean;
  small?: boolean;
  full?: boolean;
  onClick?: () => void;
  className?: string;
}

export function Button({ children, primary, small, full, onClick, className }: ButtonProps) {
  return (
    <button
      onClick={onClick}
      className={[
        "inline-flex items-center justify-center rounded-full border border-ink font-sans font-medium transition-colors",
        small ? "px-3 py-1.5 text-xs" : "px-5 py-2.5 text-sm",
        primary ? "bg-ink text-paper" : "bg-transparent text-ink",
        full ? "w-full" : "",
        className,
      ].filter(Boolean).join(" ")}
    >
      {children}
    </button>
  );
}
```

- [ ] **Step 4: Commit**

```bash
git add components/ui/
git commit -m "feat: add Wordmark, Chip, Button UI primitives"
```

---

### Task 5: UI primitives — Input, Squiggle, SectionHead

**Files:**
- Create: `components/ui/Input.tsx`
- Create: `components/ui/Squiggle.tsx`
- Create: `components/ui/SectionHead.tsx`

- [ ] **Step 1: Create `Input.tsx`**

```tsx
// components/ui/Input.tsx
interface InputProps {
  placeholder?: string;
  value?: string;
  big?: boolean;
  onChange?: (v: string) => void;
}

export function Input({ placeholder = "Tell Soulra what's on your mind…", value, big, onChange }: InputProps) {
  return (
    <div
      className={[
        "border border-ink rounded-xl bg-paper flex items-end gap-2.5 font-sans",
        big ? "p-4 min-h-[88px]" : "p-3 min-h-[44px]",
      ].join(" ")}
    >
      <div className={["flex-1 leading-relaxed", value ? "text-ink" : "text-muted"].join(" ")}
           style={{ fontSize: big ? 15 : 13 }}>
        {value || placeholder}
      </div>
      <span className="font-mono text-[10px] text-muted">↵ send</span>
    </div>
  );
}
```

- [ ] **Step 2: Create `Squiggle.tsx`**

```tsx
// components/ui/Squiggle.tsx
interface SquiggleProps { width?: number; color?: string; className?: string }

export function Squiggle({ width = 80, color = "#1d1b18", className }: SquiggleProps) {
  return (
    <svg width={width} height={6} viewBox={`0 0 ${width} 6`} className={className}>
      <path
        d={`M 0 3 Q ${width*0.15} 0, ${width*0.3} 3 T ${width*0.6} 3 T ${width*0.9} 3 T ${width} 3`}
        fill="none" stroke={color} strokeWidth={1.2} strokeLinecap="round"
      />
    </svg>
  );
}
```

- [ ] **Step 3: Create `SectionHead.tsx`**

```tsx
// components/ui/SectionHead.tsx
interface SectionHeadProps {
  kicker?: string;
  title?: string;
  sub?: string;
  className?: string;
}

export function SectionHead({ kicker, title, sub, className }: SectionHeadProps) {
  return (
    <div className={className}>
      {kicker && (
        <div className="font-mono text-[10px] text-muted uppercase tracking-widest mb-2">{kicker}</div>
      )}
      {title && (
        <div className="font-serif text-[28px] leading-tight font-medium">{title}</div>
      )}
      {sub && (
        <div className="text-sm text-muted mt-2 leading-relaxed">{sub}</div>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Commit**

```bash
git add components/ui/
git commit -m "feat: add Input, Squiggle, SectionHead UI primitives"
```

---

### Task 6: Sidebar navigation component

**Files:**
- Create: `components/layout/Sidebar.tsx`

- [ ] **Step 1: Create `Sidebar.tsx`**

```tsx
// components/layout/Sidebar.tsx
"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Wordmark } from "@/components/ui/Wordmark";

const NAV_ITEMS = [
  { href: "/home",    label: "Today",            glyph: "·" },
  { href: "/chat",    label: "New conversation", glyph: "+" },
  { href: "/journal", label: "Journal",          glyph: "◇" },
  { href: "/traditions", label: "Traditions",    glyph: "◯" },
  { href: "/daily",   label: "Daily practice",   glyph: "✓" },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-[220px] border-r border-line bg-paper-alt flex flex-col flex-shrink-0">
      <div className="px-4 py-5 pb-[18px]">
        <Wordmark size={18} />
      </div>
      <nav className="flex flex-col gap-1 px-4">
        {NAV_ITEMS.map(item => {
          const active = pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={[
                "flex items-center gap-2.5 px-2.5 py-2 rounded-md text-sm text-ink transition-colors",
                active ? "bg-paper border border-line" : "border border-transparent hover:bg-paper/50",
              ].join(" ")}
            >
              <span className="font-mono text-muted w-3 text-[11px]">{item.glyph}</span>
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>
      <div className="mt-auto px-4 py-3 border-t border-line">
        <p className="font-mono text-[10px] text-muted leading-relaxed">
          Free · 3 of 5<br />queries this week
        </p>
      </div>
    </aside>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add components/layout/Sidebar.tsx
git commit -m "feat: add Sidebar nav component with active state"
```

---

### Task 7: Page shells (Home, Chat, Journal, Daily)

**Files:**
- Create: `app/home/page.tsx`
- Create: `app/chat/page.tsx`
- Create: `app/journal/page.tsx`
- Create: `app/daily/page.tsx`

- [ ] **Step 1: Create `app/home/page.tsx`**

```tsx
// app/home/page.tsx
import { Sidebar } from "@/components/layout/Sidebar";

export default function HomePage() {
  return (
    <div className="flex h-screen bg-paper overflow-hidden">
      <Sidebar />
      <main className="flex-1 overflow-auto p-10">
        <div className="font-mono text-[10px] text-muted uppercase tracking-widest">home · today</div>
        <div className="font-serif text-4xl mt-2">Welcome back.</div>
      </main>
    </div>
  );
}
```

- [ ] **Step 2: Create `app/chat/page.tsx`**

```tsx
// app/chat/page.tsx
import { Sidebar } from "@/components/layout/Sidebar";

export default function ChatPage() {
  return (
    <div className="flex h-screen bg-paper overflow-hidden">
      <Sidebar />
      <main className="flex-1 overflow-auto p-10">
        <div className="font-mono text-[10px] text-muted uppercase tracking-widest">conversation</div>
        <div className="font-serif text-4xl mt-2">What is asking for your attention?</div>
      </main>
    </div>
  );
}
```

- [ ] **Step 3: Create `app/journal/page.tsx`**

```tsx
// app/journal/page.tsx
import { Sidebar } from "@/components/layout/Sidebar";

export default function JournalPage() {
  return (
    <div className="flex h-screen bg-paper overflow-hidden">
      <Sidebar />
      <main className="flex-1 overflow-auto p-10">
        <div className="font-mono text-[10px] text-muted uppercase tracking-widest">your journal</div>
        <div className="font-serif text-4xl mt-2">Wisdom you've kept.</div>
      </main>
    </div>
  );
}
```

- [ ] **Step 4: Create `app/daily/page.tsx`**

```tsx
// app/daily/page.tsx
import { Sidebar } from "@/components/layout/Sidebar";

export default function DailyPage() {
  return (
    <div className="flex h-screen bg-paper overflow-hidden">
      <Sidebar />
      <main className="flex-1 overflow-auto p-10">
        <div className="font-mono text-[10px] text-muted uppercase tracking-widest">daily practice</div>
        <div className="font-serif text-4xl mt-2">Today's teaching.</div>
      </main>
    </div>
  );
}
```

- [ ] **Step 5: Run dev and verify all routes work**

```bash
npm run dev &
sleep 5
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/home
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/chat
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/journal
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/daily
kill %1
```

Expected: `200` for all four.

- [ ] **Step 6: Run type check**

```bash
npm run build 2>&1 | tail -20
```

Expected: no TypeScript errors.

- [ ] **Step 7: Commit**

```bash
git add app/
git commit -m "feat: scaffold Home, Chat, Journal, Daily page shells with Sidebar"
```

---

## Self-Review

**Spec coverage:**
- ✅ Design tokens extracted from wireframes
- ✅ Fonts: Cormorant Garamond, Inter, JetBrains Mono, Caveat
- ✅ Color palette: ink, paper, paperAlt, line, lineSoft, muted, accent, accentSoft, danger
- ✅ Sidebar nav with active state
- ✅ All 4 MVP routes scaffolded
- ✅ WfWordmark → Wordmark, WfChip → Chip, WfBtn → Button, WfInput → Input, WfSquiggle → Squiggle, WfSectionHead → SectionHead

**Placeholder scan:** None — every step has code.

**Type consistency:** `tokens` export is typed `as const`. All component props have explicit interfaces.
