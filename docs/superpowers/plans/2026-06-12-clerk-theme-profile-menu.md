# Themed Clerk Auth + Sidebar Profile Menu Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restyle Clerk's auth UI (sign-in/sign-up pages and the landing-page sign-in modal) to match Soulra's paper/ink/accent color theme, and replace the Sidebar's static placeholder with a real profile menu showing the user's avatar, name, email, token usage, admin link, and sign-out.

**Architecture:** A single shared `Appearance` object (`lib/clerk-theme.ts`) passed to `<ClerkProvider>` themes every Clerk-rendered surface (standalone pages + `openSignIn()` modal) globally. The landing page gains a small `AuthCta` helper component that branches on `useUser().isSignedIn` to either link to `/home` or call `useClerk().openSignIn()`. A new `UserMenu` client component replaces the Sidebar's placeholder block, combining Clerk's `useUser()`/`useClerk()` with the already-existing `getMe()` (`/api/v1/me`) data for token usage.

**Tech Stack:** Next.js 16 (App Router), React 19, `@clerk/nextjs` 7.5, Tailwind CSS 4 (custom theme tokens in `app/globals.css`), TypeScript, no frontend test runner — verification is via `npm run typecheck`, `npm run lint`, and manual browser checks against the dev server.

---

### Task 1: Shared Clerk appearance theme

**Files:**
- Create: `lib/clerk-theme.ts`

This project uses Tailwind CSS v4 and Clerk's current SDK (v7, "Core 3"). In this version, `colorText`, `colorTextSecondary`, and `colorInputBackground` are deprecated in favor of `colorForeground`, `colorMutedForeground`, and `colorInput`. Tailwind utility classes passed via `elements` need `cssLayerName` set so they win the CSS cascade against Clerk's own styles (see Task 2, Step 1 for the matching `globals.css` change).

- [ ] **Step 1: Create the theme file**

```ts
// lib/clerk-theme.ts
export const clerkAppearance = {
  cssLayerName: "clerk",
  variables: {
    colorPrimary: "#1d1b18",
    colorBackground: "#f7f4ee",
    colorForeground: "#1d1b18",
    colorMutedForeground: "#7d7568",
    colorMuted: "#efeae0",
    colorInput: "#efeae0",
    colorBorder: "#cdc6b8",
    colorDanger: "#8a4a3c",
    borderRadius: "0.75rem",
    fontFamily: "var(--font-inter), system-ui, sans-serif",
  },
  elements: {
    headerTitle: "font-serif",
    formButtonPrimary: "rounded-full normal-case text-sm font-medium shadow-none",
    footerActionLink: "text-[#7a5c3e] hover:text-[#1d1b18]",
  },
};
```

- [ ] **Step 2: Typecheck**

Run: `npm run typecheck`
Expected: passes (no errors related to `lib/clerk-theme.ts`)

- [ ] **Step 3: Commit**

```bash
git add lib/clerk-theme.ts
git commit -m "feat: add shared Clerk appearance theme"
```

---

### Task 2: Apply the theme via ClerkProvider

**Files:**
- Modify: `app/layout.tsx:47,54`
- Modify: `app/globals.css:1`

- [ ] **Step 1: Set up the Tailwind v4 CSS layer order**

In `app/globals.css`, the file currently starts with:

```css
@import "tailwindcss";
```

Change it to:

```css
@layer theme, base, clerk, components, utilities;
@import "tailwindcss";
```

This ensures Tailwind's utility classes (used in `lib/clerk-theme.ts`'s `elements` overrides) are applied after Clerk's own styles, which are placed in the `clerk` layer via `cssLayerName: "clerk"`.

- [ ] **Step 2: Import the theme and pass it to ClerkProvider**

In `app/layout.tsx`, add the import near the top (after the `"./globals.css"` import):

```ts
import "./globals.css";
import { clerkAppearance } from "@/lib/clerk-theme";
```

Then change:

```tsx
    <ClerkProvider>
```

to:

```tsx
    <ClerkProvider appearance={clerkAppearance}>
```

- [ ] **Step 3: Typecheck**

Run: `npm run typecheck`
Expected: passes

- [ ] **Step 3: Manual verification — themed sign-in page**

Run: `npm run dev` (in `/Volumes/External/soulra`)
Open `http://localhost:3000/sign-in` in a browser.
Expected: the card background is the warm paper color (`#f7f4ee`), the "Continue" button is a dark pill (`#1d1b18` background, light text), input fields have the paper-alt background with the line-colored border, and the header title uses the serif font — no blue Clerk-default colors remain. The "Don't have an account? Sign up" link is still present and uses the accent brown color. (The "Development mode" notice is a Clerk test-key indicator, not themeable via `appearance` — it's expected to remain visible until real Clerk keys are configured; this matches the design spec's noted limitation.)

- [ ] **Step 4: Commit**

```bash
git add app/layout.tsx
git commit -m "feat: theme Clerk components via ClerkProvider appearance"
```

---

### Task 3: Brand the standalone sign-in/sign-up pages

**Files:**
- Modify: `app/sign-in/[[...sign-in]]/page.tsx`
- Modify: `app/sign-up/[[...sign-up]]/page.tsx`

- [ ] **Step 1: Update the sign-in page**

Replace the full contents of `app/sign-in/[[...sign-in]]/page.tsx` with:

```tsx
import { SignIn } from "@clerk/nextjs";
import { Wordmark } from "@/components/ui";

export default function SignInPage() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center gap-6 bg-paper">
      <Wordmark size={22} />
      <SignIn />
    </div>
  );
}
```

- [ ] **Step 2: Update the sign-up page**

Replace the full contents of `app/sign-up/[[...sign-up]]/page.tsx` with:

```tsx
import { SignUp } from "@clerk/nextjs";
import { Wordmark } from "@/components/ui";

export default function SignUpPage() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center gap-6 bg-paper">
      <Wordmark size={22} />
      <SignUp />
    </div>
  );
}
```

- [ ] **Step 3: Typecheck**

Run: `npm run typecheck`
Expected: passes

- [ ] **Step 4: Manual verification**

With `npm run dev` running, open `http://localhost:3000/sign-in` and `http://localhost:3000/sign-up`.
Expected: the "Soulra" wordmark appears centered above the themed Clerk card on both pages.

- [ ] **Step 5: Commit**

```bash
git add "app/sign-in/[[...sign-in]]/page.tsx" "app/sign-up/[[...sign-up]]/page.tsx"
git commit -m "feat: add Soulra wordmark to sign-in/sign-up pages"
```

---

### Task 4: Landing page — auth-aware CTAs that open a themed sign-in modal

**Files:**
- Modify: `components/screens/LandingScreen.tsx:1-4,114-145,228-236`

- [ ] **Step 1: Add imports and the `AuthCta` helper component**

In `components/screens/LandingScreen.tsx`, change the top imports from:

```tsx
"use client";
import { useState } from "react";
import Link from "next/link";
import { Wordmark, Button, Squiggle } from "@/components/ui";
```

to:

```tsx
"use client";
import { useState } from "react";
import Link from "next/link";
import { useUser, useClerk } from "@clerk/nextjs";
import { Wordmark, Button, Squiggle } from "@/components/ui";
```

Then, directly above `export function LandingScreen() {`, add the helper component:

```tsx
function AuthCta({
  signedInLabel,
  signedOutLabel,
}: {
  signedInLabel: string;
  signedOutLabel: string;
}) {
  const { isSignedIn } = useUser();
  const { openSignIn } = useClerk();

  if (isSignedIn) {
    return (
      <Link href="/home">
        <Button primary>{signedInLabel}</Button>
      </Link>
    );
  }

  return (
    <Button primary onClick={() => openSignIn()}>
      {signedOutLabel}
    </Button>
  );
}
```

- [ ] **Step 2: Replace the header CTA**

Change:

```tsx
      <header className="flex items-center justify-between px-12 py-7 border-b border-line">
        <Wordmark size={22} />
        <Link href="/home">
          <Button primary>Enter Soulra →</Button>
        </Link>
      </header>
```

to:

```tsx
      <header className="flex items-center justify-between px-12 py-7 border-b border-line">
        <Wordmark size={22} />
        <AuthCta signedInLabel="Go to app →" signedOutLabel="Sign in →" />
      </header>
```

- [ ] **Step 3: Replace the hero CTA**

Change:

```tsx
        <div className="flex gap-3 mt-9">
          <Link href="/home">
            <Button primary>Begin a conversation →</Button>
          </Link>
          <a href="#how-it-works">
            <Button>See how it works</Button>
          </a>
        </div>
```

to:

```tsx
        <div className="flex gap-3 mt-9">
          <AuthCta signedInLabel="Begin a conversation →" signedOutLabel="Begin a conversation →" />
          <a href="#how-it-works">
            <Button>See how it works</Button>
          </a>
        </div>
```

- [ ] **Step 4: Replace the closing CTA**

Change:

```tsx
        <Link href="/home">
          <Button primary>Start a conversation →</Button>
        </Link>
```

to:

```tsx
        <AuthCta signedInLabel="Start a conversation →" signedOutLabel="Start a conversation →" />
```

(This is inside the `<section>` that previously wrapped the `<Link>` directly — `AuthCta` renders either a `<Link><Button/></Link>` or a `<Button/>`, both valid direct children of that `<section>`.)

- [ ] **Step 5: Typecheck**

Run: `npm run typecheck`
Expected: passes

- [ ] **Step 6: Manual verification — signed out**

With `npm run dev` running and signed out (open an incognito window or sign out via an existing session), open `http://localhost:3000/`.
Expected: header shows "Sign in →", hero shows "Begin a conversation →", closing section shows "Start a conversation →". Clicking any of them opens Clerk's sign-in modal in place (no navigation), themed with the paper/ink palette from Task 1.

- [ ] **Step 7: Manual verification — signed in**

Sign in (via the modal from Step 6, using a real or test account).
Expected: back on `/`, header now shows "Go to app →", hero shows "Begin a conversation →", closing section shows "Start a conversation →" — all three now link to `/home` (no modal).

- [ ] **Step 8: Commit**

```bash
git add components/screens/LandingScreen.tsx
git commit -m "feat: auth-aware landing page CTAs with themed sign-in modal"
```

---

### Task 5: `UserMenu` component

**Files:**
- Create: `components/layout/UserMenu.tsx`

- [ ] **Step 1: Create the component**

```tsx
// components/layout/UserMenu.tsx
"use client";
import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { useUser, useClerk } from "@clerk/nextjs";
import type { MeData } from "@/lib/api";

export function UserMenu({ me }: { me: MeData | null }) {
  const { user } = useUser();
  const { signOut } = useClerk();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function onClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, [open]);

  if (!user) return null;

  const name = user.fullName || user.primaryEmailAddress?.emailAddress || "Account";
  const email = user.primaryEmailAddress?.emailAddress ?? "";
  const initial = name.charAt(0).toUpperCase();
  const tokensLeft = me ? Math.max(0, me.token_limit - me.tokens_used) : null;
  const pct = me && me.token_limit > 0
    ? Math.min(100, (me.tokens_used / me.token_limit) * 100)
    : 0;

  return (
    <div ref={ref} className="mt-auto px-4 py-3 border-t border-line relative">
      <button
        onClick={() => setOpen(o => !o)}
        className="flex items-center gap-2.5 w-full px-2.5 py-2 rounded-md text-sm text-ink border border-transparent hover:bg-paper/50 transition-colors"
      >
        {user.imageUrl ? (
          <Image
            src={user.imageUrl}
            alt=""
            width={28}
            height={28}
            unoptimized
            className="w-7 h-7 rounded-full flex-shrink-0"
          />
        ) : (
          <span className="w-7 h-7 rounded-full bg-ink text-paper flex items-center justify-center text-[12px] font-medium flex-shrink-0">
            {initial}
          </span>
        )}
        <span className="truncate flex-1 text-left">{name}</span>
        <span className="font-mono text-muted text-[11px]">▾</span>
      </button>

      {open && (
        <div className="absolute left-4 right-4 bottom-full mb-2 bg-paper border border-line rounded-xl shadow-sm p-3 z-10">
          <div className="text-sm font-medium truncate">{name}</div>
          {email && (
            <div className="font-mono text-[10px] text-muted truncate mt-0.5">{email}</div>
          )}

          {me && (
            <>
              <div className="border-t border-line-soft my-2" />
              <div className="font-mono text-[9px] text-muted uppercase tracking-widest mb-1.5">
                Token usage
              </div>
              <div className="h-1.5 rounded-full bg-paper-alt overflow-hidden">
                <div className="h-full bg-accent" style={{ width: `${pct}%` }} />
              </div>
              <div className="font-mono text-[10px] text-muted mt-1.5">
                {tokensLeft!.toLocaleString()} tokens left
              </div>
            </>
          )}

          {me?.role === "admin" && (
            <>
              <div className="border-t border-line-soft my-2" />
              <Link
                href="/admin/users"
                className="font-mono text-[9px] text-accent uppercase tracking-widest hover:underline"
              >
                Admin dashboard →
              </Link>
            </>
          )}

          <div className="border-t border-line-soft my-2" />
          <button
            onClick={() => signOut()}
            className="font-mono text-[11px] text-danger hover:underline"
          >
            Sign out
          </button>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Typecheck**

Run: `npm run typecheck`
Expected: passes

- [ ] **Step 3: Commit**

```bash
git add components/layout/UserMenu.tsx
git commit -m "feat: add UserMenu component with token usage dropdown"
```

---

### Task 6: Wire `UserMenu` into the Sidebar

**Files:**
- Modify: `components/layout/Sidebar.tsx:1-9,57-67,100-104`

- [ ] **Step 1: Import UserMenu**

Change:

```tsx
import { Wordmark } from "@/components/ui";
import { listConversations, formatRelativeDate, getMe } from "@/lib/api";
import type { Conversation, MeData } from "@/lib/api";
```

to:

```tsx
import { Wordmark } from "@/components/ui";
import { UserMenu } from "./UserMenu";
import { listConversations, formatRelativeDate, getMe } from "@/lib/api";
import type { Conversation, MeData } from "@/lib/api";
```

- [ ] **Step 2: Remove the separate admin nav-link block**

Remove this block entirely (its functionality moves into `UserMenu`'s admin link):

```tsx
      {me?.role === "admin" && (
        <div className="px-4 mt-1">
          <Link
            href="/admin/users"
            className="flex items-center gap-2.5 px-2.5 py-2 rounded-md text-sm text-ink border border-transparent hover:bg-paper/50"
          >
            <span className="font-mono text-muted w-3 text-[11px]">▲</span>
            <span>Admin</span>
          </Link>
        </div>
      )}

```

- [ ] **Step 3: Replace the placeholder footer block**

Change:

```tsx
      <div className="mt-auto px-4 py-3 border-t border-line">
        <p className="font-mono text-[10px] text-muted leading-relaxed">
          Free · 3 of 5<br />queries this week
        </p>
      </div>
```

to:

```tsx
      <UserMenu me={me} />
```

- [ ] **Step 4: Typecheck and lint**

Run: `npm run typecheck && npm run lint`
Expected: both pass. (If lint flags `Link` as now unused in `Sidebar.tsx`, leave it — `Link` is still used by `NAV_ITEMS` and recent-conversations rendering above; only remove an import if the linter specifically reports it as unused.)

- [ ] **Step 5: Manual verification**

With `npm run dev` running and signed in, open `http://localhost:3000/home`.
Expected: the Sidebar's bottom section shows your avatar (or initial-letter circle if no Clerk avatar) and name. Clicking it opens a dropdown above the button showing your name/email, a token-usage progress bar with "`N` tokens left", an "Admin dashboard →" link only if your account's role is `admin`, and a "Sign out" button. Clicking outside the dropdown closes it. Clicking "Sign out" signs you out and returns you to the signed-out landing page.

- [ ] **Step 6: Commit**

```bash
git add components/layout/Sidebar.tsx
git commit -m "feat: replace sidebar placeholder with UserMenu profile dropdown"
```

---

### Task 7: Final check

**Files:** none (verification only)

- [ ] **Step 1: Full typecheck and lint**

Run: `npm run typecheck && npm run lint`
Expected: both pass with no errors.

- [ ] **Step 2: Full manual walkthrough**

With `npm run dev` running:
1. Signed out, visit `/` — themed CTAs open the themed sign-in modal.
2. Sign in — `/` now shows "Go to app →"; `/home` Sidebar shows the new `UserMenu`.
3. Open the `UserMenu` dropdown — verify name, email, token bar, "tokens left" count match the values returned by `GET /api/v1/me` (check via browser devtools network tab or `curl` with a valid session token).
4. If your test account has `role: "admin"` (set via `/admin/users` or directly in the DB), confirm the "Admin dashboard →" link appears and navigates to `/admin/users`.
5. Click "Sign out" — confirm it returns to the signed-out landing page and the Sidebar/UserMenu no longer apply (since `/home` is now protected and redirects to `/sign-in` or `/`).
6. Visit `/sign-in` and `/sign-up` directly — confirm both show the Soulra wordmark above the themed card.

No code changes expected from this task — it's a final end-to-end sanity pass over Tasks 1–6.
