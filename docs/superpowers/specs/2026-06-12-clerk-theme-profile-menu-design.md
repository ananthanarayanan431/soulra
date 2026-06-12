# Themed Clerk Auth + Sidebar Profile Menu

**Date:** 2026-06-12
**Status:** Approved

## Problem

The default Clerk `<SignIn/>`/`<SignUp/>` UI (white card, blue accents, "Secured by Clerk" badge) doesn't match Soulra's warm paper/ink/accent color theme. Separately, the landing page sends signed-out visitors to a standalone `/sign-in` page rather than letting them authenticate inline, and the Sidebar's "Free · 3 of 5 queries this week" block is static placeholder text instead of real account info — there's no way for a signed-in user to see their token usage or sign out without leaving the app shell.

## Approach

1. Theme Clerk globally via the `appearance` prop on `<ClerkProvider>` so `<SignIn/>`, `<SignUp/>`, and Clerk's modal/`useClerk()` flows all inherit Soulra's palette and typography — no per-page theming needed.
2. On the landing page, signed-out CTAs open Clerk's themed sign-in modal via `useClerk().openSignIn()` instead of navigating to `/sign-in`; signed-in visitors see a "Go to app" CTA instead. The standalone `/sign-in` and `/sign-up` routes remain (for direct links / middleware redirects) and inherit the same theme.
3. Replace the static placeholder block at the bottom of `Sidebar.tsx` with a new `UserMenu` component: an avatar button (Clerk `useUser()`) that toggles a themed dropdown showing name/email, a token usage bar + remaining count (from the existing `/api/v1/me` endpoint via `getMe()`), an admin badge/link when applicable, and a sign-out action.
4. No backend changes — `/api/v1/me` already returns `token_limit` and `tokens_used`, which is everything the dropdown needs.

---

## Section 1: Shared Clerk theme (`lib/clerk-theme.ts`)

New file exporting a single `clerkAppearance` object (typed as Clerk's `Appearance`):

- `variables`:
  - `colorPrimary` → `--color-ink` (`#1d1b18`)
  - `colorBackground` → `--color-paper` (`#f7f4ee`)
  - `colorInputBackground` → `--color-paper-alt` (`#efeae0`)
  - `colorText` → `--color-ink`
  - `colorTextSecondary` → `--color-muted` (`#7d7568`)
  - `colorDanger` → `--color-danger` (`#8a4a3c`)
  - `borderRadius` → `0.75rem` (matches `rounded-xl` used elsewhere)
  - `fontFamily` → Inter (`var(--font-inter)`)
- `elements` overrides (only where the default visibly clashes):
  - `card` → remove shadow, add `border border-[#cdc6b8]` (`--color-line`), `bg-paper`
  - `headerTitle` / `headerSubtitle` → serif font for the title, muted color for subtitle, matching `Wordmark`/heading style elsewhere
  - `formButtonPrimary` → pill shape (`rounded-full`), `bg-ink text-paper hover:bg-ink/90`, matching `components/ui/Button.tsx`'s `primary` variant
  - `socialButtonsBlockButton` / `formFieldInput` → `rounded-xl border-line`, paper-alt background
  - `footerActionLink` → `--color-accent` (`#7a5c3e`)
  - `dividerLine` / `dividerText` → `--color-line-soft` / `--color-muted`
  - hide the Clerk "Development mode" / "Secured by Clerk" footer badge via `elements.footer` / `footerAction` visibility tweaks (Clerk's documented `elements.footer: { display: "none" }` for the badge specifically — the "Sign up" / "Sign in" footer action link stays)

Applied via `<ClerkProvider appearance={clerkAppearance}>` in `app/layout.tsx`. This single change themes `<SignIn/>`, `<SignUp/>`, and any Clerk-rendered modal (`openSignIn()`/`openSignUp()`).

## Section 2: Landing page (`components/screens/LandingScreen.tsx`)

- Add `"use client"` is already present; import `useUser` and `useClerk` from `@clerk/nextjs`.
- Derive `const { isSignedIn } = useUser();` and `const clerk = useClerk();`.
- Header CTA ("Enter Soulra →"):
  - Signed in → `<Link href="/home"><Button primary>Go to app →</Button></Link>` (unchanged target, new label)
  - Signed out → `<Button primary onClick={() => clerk.openSignIn()}>Sign in →</Button>` (no `Link`/navigation — opens Clerk's modal in place)
- Hero CTA ("Begin a conversation →") and closing-section CTA ("Start a conversation →"): same conditional — signed-in users go to `/home`, signed-out users get `openSignIn()`.
- "See how it works" anchor link is unaffected (no auth gate).
- While Clerk is loading (`isLoaded === false`), render the signed-out variant (buttons open the sign-in modal) to avoid a layout flash — Clerk's modal itself handles its own loading state.

## Section 3: Sign-in / sign-up routes

`app/sign-in/[[...sign-in]]/page.tsx` and `app/sign-up/[[...sign-up]]/page.tsx`:
- Keep the existing `bg-paper` full-height centering wrapper.
- Add a `<Wordmark size={22} />` above the `<SignIn/>`/`<SignUp/>` component (wrapped in a `flex flex-col items-center gap-6` container) so the page has Soulra branding instead of a bare card.
- No other structural changes — theming comes from `ClerkProvider`'s `appearance` (Section 1).

## Section 4: `UserMenu` component (`components/layout/UserMenu.tsx`, new)

A client component rendered at the bottom of `Sidebar.tsx`, replacing the current:
```tsx
<div className="mt-auto px-4 py-3 border-t border-line">
  <p className="font-mono text-[10px] text-muted leading-relaxed">
    Free · 3 of 5<br />queries this week
  </p>
</div>
```

**Data sources:**
- `useUser()` (Clerk) → `user.imageUrl`, `user.fullName`/`user.firstName`, `user.primaryEmailAddress`
- `getMe()` (existing `lib/api.ts`, hits `/api/v1/me`) → `{ name, email, role, token_limit, tokens_used }` — fetched once on mount via `useEffect`, same pattern already used in `Sidebar.tsx`'s existing `getMe().then(setMe)`. (Sidebar already calls `getMe()` for the admin-link check — `UserMenu` can either receive `me` as a prop from `Sidebar` to avoid a duplicate fetch, or do its own fetch. **Decision: pass `me` down as a prop** to avoid double-fetching `/api/v1/me`.)

**Structure:**
- Outer `<div className="mt-auto px-4 py-3 border-t border-line relative">`
- Button (avatar + name, full width, `rounded-md` hover like nav items):
  - `<img>` (Clerk `imageUrl`, `w-7 h-7 rounded-full`) — fallback to a plain ink-colored circle with the first letter of the name/email if `imageUrl` is missing
  - Name (or email if no name) in `text-sm`, truncated
  - Small chevron/glyph (`▾` in `font-mono text-muted`) indicating it's expandable
- Clicking toggles `open` state; a `useEffect` with a `mousedown` listener on `document` closes the dropdown on outside click (cleanup on unmount).
- Dropdown panel (`open === true`): absolutely positioned above the button (`bottom-full mb-2`, since it's at the bottom of the sidebar), `bg-paper border border-line rounded-xl shadow-sm p-3 w-[calc(100%-2rem)]`:
  - Name (`text-sm font-medium`) + email (`font-mono text-[10px] text-muted truncate`)
  - Divider (`border-t border-line-soft my-2`)
  - Token usage:
    - Label row: `font-mono text-[9px] text-muted uppercase tracking-widest` → "Token usage"
    - Progress bar: `h-1.5 rounded-full bg-paper-alt overflow-hidden`, inner `bg-accent` div with `width: ${pct}%` where `pct = Math.min(100, (tokens_used / token_limit) * 100)`
    - Below bar: `font-mono text-[10px] text-muted` → `{formatNumber(token_limit - tokens_used)} tokens left` (reuse/extend a small number formatter — check `lib/utils.ts` for an existing one, else add a minimal `toLocaleString()`-based helper)
  - If `me.role === "admin"`: a row with `font-mono text-[9px] text-accent uppercase tracking-widest` "Admin" badge — link to `/admin/users` (this can replace the existing separate "Admin" nav-link block in `Sidebar.tsx`, consolidating admin access into the profile menu)
  - Divider
  - "Sign out" button (`text-sm text-danger`, full width, left-aligned) → `useClerk().signOut()`

**Loading/empty state:** if `me` is `null` (still loading or fetch failed), render just the avatar + name from Clerk's `useUser()` (always available client-side once loaded) with the dropdown showing only "Sign out" — token section and admin badge are omitted rather than showing placeholder zeros.

## Section 5: `Sidebar.tsx` changes

- Remove the separate "Admin" nav-link block (Section 4 consolidates it into `UserMenu`).
- Replace the bottom placeholder `<div>` with `<UserMenu me={me} />`.
- `me` state (`MeData | null`) already exists in `Sidebar` via the existing `getMe().then(setMe)` effect — no new fetch.

## Section 6: Backend

No changes. `/api/v1/me` (`soulra/api/v1/me.py`, already registered in `main.py`) returns `MeOut { id, email, name, role, token_limit, tokens_used }`, which covers every field `UserMenu` needs.

---

## Testing

- Manual: load `/` signed out → header/hero CTAs open themed Clerk sign-in modal (paper background, ink primary button, no blue/Clerk branding mismatch, no "Development mode" badge visible... note: dev-mode badge may still appear since it's tied to using test API keys, not the `appearance` prop — confirm during implementation whether `elements.footer` hides it or whether it's a key-environment thing that can't be themed away).
- Manual: sign in → `/` now shows "Go to app →"; `/home` Sidebar shows avatar, name, token bar with correct remaining count, admin link only for admin users, sign-out works and returns to signed-out landing state.
- Manual: `/sign-in` and `/sign-up` directly (e.g. via a stale bookmark or middleware redirect) show the same themed card with Wordmark above it.
- No new automated tests — this is a presentational/UI change with no new backend logic; existing `test_token_usage.py` and `/api/v1/me` tests are unaffected.

## Out of scope

- Editing `token_limit` from the UI (admin-only, already covered by `/admin/users`)
- Per-conversation token usage breakdown in the dropdown (covered by `/admin/usage` for admins)
- Custom Clerk `UserProfile` page theming (not used — we're not linking to Clerk's full account-management UI)
- Changing the `/api/v1/me` schema or adding new fields
