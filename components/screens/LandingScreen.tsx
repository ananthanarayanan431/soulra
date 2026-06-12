"use client";
import { useState } from "react";
import Link from "next/link";
import { useUser, useClerk } from "@clerk/nextjs";
import { Logo, Button, Squiggle } from "@/components/ui";

const PRINCIPLES = [
  {
    title: "Not therapy. Not a search engine.",
    body: "Soulra doesn't diagnose or prescribe, and it doesn't hand you a single ranked answer. It listens to what you bring, then shows you how traditions separated by centuries and continents have wrestled with knots like yours.",
  },
  {
    title: "Many voices, not one verdict.",
    body: "A Stoic and a Sufi won't always agree — and Soulra won't paper over that. The disagreement between traditions is often where your own thinking actually begins.",
  },
  {
    title: "Practice, not just insight.",
    body: "A good conversation can fade by the next morning. So every conversation can seed a 7-day practice thread — small, concrete ways to carry what you found into the week ahead.",
  },
];

const STEPS = [
  {
    n: "01",
    glyph: "◎",
    title: "Bring a situation",
    body: "Not a query — a weight. Something you're carrying, avoiding, or trying to understand. Type it like you'd say it to a person, not a search bar.",
  },
  {
    n: "02",
    glyph: "◯",
    title: "The traditions respond",
    body: "Soulra searches across Stoic, Vedanta, Buddhist, Sufi and other lineages and brings back passages that actually speak to your situation — each one cited back to its source text.",
  },
  {
    n: "03",
    glyph: "◻",
    title: "A 7-day thread begins",
    body: "Every conversation can seed a week of practice: a teaching each morning drawn from what the traditions said to you, a question each evening to help it land.",
  },
  {
    n: "04",
    glyph: "◇",
    title: "Wisdom accumulates",
    body: "Save the lines that stay with you. Tag them. Mark when they actually show up in a real moment. Over time, your journal becomes a record of who you're becoming.",
  },
];

const LIBRARY = [
  "Stoicism", "Vedanta", "Buddhism", "Taoism", "Sufism",
  "Jewish wisdom", "Christian mystics", "Zen", "Indigenous & earth traditions",
];

const FAQ = [
  {
    q: "Is Soulra therapy?",
    a: "No. Soulra doesn't diagnose, treat, or replace professional care. It's a space to think alongside centuries of contemplative wisdom — a different kind of company for the questions that don't have easy answers.",
  },
  {
    q: "Do I need to know anything about these traditions first?",
    a: "Not at all. You bring the situation; Soulra brings the context — who said what, where, and why it might speak to you. No background reading required.",
  },
  {
    q: "How is this different from a general AI chatbot?",
    a: "Soulra is built around primary wisdom texts, not generic advice. Every passage is sourced and cited, multiple traditions are shown side by side rather than collapsed into one verdict, and a conversation can grow into a week of practice rather than ending when the chat does.",
  },
  {
    q: "What happens to the lines I save?",
    a: "They go into your personal journal — searchable, taggable, and markable as “applied” once they actually show up in a real moment. Over time it becomes a record of what's actually shaped you.",
  },
  {
    q: "Which traditions does it draw from?",
    a: "Stoicism, Vedanta, Buddhism, Taoism, Sufism, Jewish wisdom, Christian mysticism, Zen, and indigenous & earth traditions — with more being added as the library grows.",
  },
];

function FaqItem({
  q,
  a,
  open,
  onToggle,
}: {
  q: string;
  a: string;
  open: boolean;
  onToggle: () => void;
}) {
  return (
    <div className="border-t border-line-soft first:border-t-0">
      <button
        onClick={onToggle}
        aria-expanded={open}
        className="w-full flex items-center justify-between gap-6 py-7 text-left"
      >
        <span className="font-serif text-[21px] leading-snug">{q}</span>
        <span
          className="font-mono text-[16px] text-muted flex-shrink-0 transition-transform duration-200"
          style={{ display: "inline-block", transform: open ? "rotate(45deg)" : "rotate(0deg)" }}
        >
          +
        </span>
      </button>
      {open && (
        <p className="text-[15px] text-muted leading-[1.8] pb-7 -mt-2">{a}</p>
      )}
    </div>
  );
}

function AuthCta({
  signedInLabel,
  signedOutLabel,
}: {
  signedInLabel: string;
  signedOutLabel: string;
}) {
  const { isSignedIn } = useUser();

  return (
    <Link href={isSignedIn ? "/home" : "/sign-in"}>
      <Button primary>{isSignedIn ? signedInLabel : signedOutLabel}</Button>
    </Link>
  );
}

function AuthControls() {
  const { isSignedIn } = useUser();
  const { signOut } = useClerk();

  if (isSignedIn) {
    return (
      <button
        onClick={() => signOut({ redirectUrl: "/" })}
        className="font-mono text-[12px] text-muted hover:text-ink transition-colors"
      >
        Log out
      </button>
    );
  }

  return (
    <div className="flex items-center gap-3">
      <Link href="/sign-in">
        <Button>Log in</Button>
      </Link>
      <Link href="/sign-up">
        <Button>Sign up →</Button>
      </Link>
    </div>
  );
}

function HeaderAuth() {
  return (
    <div className="flex items-center gap-5">
      <AuthControls />
      <div className="w-px h-6 bg-line" />
      <Link href="/home">
        <Button primary>Enter Soulra →</Button>
      </Link>
    </div>
  );
}

export function LandingScreen() {
  const [openFaq, setOpenFaq] = useState<number | null>(0);

  return (
    <div className="min-h-screen bg-paper text-ink">
      {/* top nav */}
      <header className="flex items-center justify-between px-12 py-7 border-b border-line">
        <Logo size={22} />
        <HeaderAuth />
      </header>

      {/* hero */}
      <section className="px-12 pt-24 pb-20 max-w-[820px]">
        <div className="font-mono text-[11px] text-muted uppercase tracking-widest mb-6">
          an ai wisdom companion
        </div>
        <h1 className="font-serif text-[60px] leading-[1.16]">
          Ancient wisdom, applied to what is alive in you <em className="text-accent">now</em>.
        </h1>
        <Squiggle width={104} className="my-7 text-accent-soft" />
        <p className="text-[17px] text-muted leading-[1.85] max-w-[660px]">
          Soulra is a conversation, not a search engine. Bring it a situation — a weight you&rsquo;re
          carrying, a question that won&rsquo;t let you go, a pattern you keep running into — and it
          draws from Stoic, Vedanta, Buddhist, Sufi and other wisdom lineages. Not to hand you
          an answer, but to show you how each tradition sees your knot.
        </p>
        <div className="flex gap-3 mt-9">
          <AuthCta signedInLabel="Begin a conversation →" signedOutLabel="Begin a conversation →" />
          <a href="#how-it-works">
            <Button>See how it works</Button>
          </a>
        </div>
      </section>

      {/* what makes it different */}
      <section className="px-12 py-20 border-t border-line bg-paper-alt">
        <div className="font-mono text-[11px] text-muted uppercase tracking-widest mb-9">
          what soulra is — and isn&rsquo;t
        </div>
        <div className="grid grid-cols-3 gap-12 max-w-[1220px]">
          {PRINCIPLES.map(p => (
            <div key={p.title}>
              <div className="font-serif text-[23px] leading-snug mb-3">{p.title}</div>
              <p className="text-[15px] text-muted leading-[1.8]">{p.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* how it works */}
      <section id="how-it-works" className="px-12 py-20 border-t border-line">
        <div className="font-mono text-[11px] text-muted uppercase tracking-widest mb-10">
          how it works
        </div>
        <div className="grid grid-cols-2 gap-x-20 gap-y-12 max-w-[1100px]">
          {STEPS.map(step => (
            <div key={step.n} className="flex gap-5">
              <div className="w-11 h-11 rounded-full border border-ink flex items-center justify-center font-mono text-[15px] flex-shrink-0">
                {step.glyph}
              </div>
              <div>
                <div className="flex items-baseline gap-2.5 mb-2">
                  <span className="font-mono text-[11px] text-muted tracking-widest">{step.n}</span>
                  <span className="font-serif text-[22px] leading-tight">{step.title}</span>
                </div>
                <p className="text-[15px] text-muted leading-[1.8] max-w-[420px]">{step.body}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* the library */}
      <section className="px-12 py-20 border-t border-line bg-paper-alt">
        <div className="font-mono text-[11px] text-muted uppercase tracking-widest mb-6">
          the library
        </div>
        <div className="flex flex-wrap gap-2.5 max-w-[820px] mb-6">
          {LIBRARY.map(name => (
            <span
              key={name}
              className="border border-ink rounded-full px-4 py-2 font-mono text-[13px] text-ink"
            >
              {name}
            </span>
          ))}
          <span className="border border-dashed border-line rounded-full px-4 py-2 font-mono text-[13px] text-muted">
            growing
          </span>
        </div>
        <p className="text-[15px] text-muted leading-[1.8] max-w-[640px]">
          Every passage Soulra draws from is sourced and cited back to its text — so when it tells
          you what Marcus Aurelius, Rumi, or the Bhagavad Gita has to say about your situation,
          you can go find the page yourself.
        </p>
      </section>

      {/* faq */}
      <section className="px-12 py-20 border-t border-line">
        <div className="font-mono text-[11px] text-muted uppercase tracking-widest mb-10">
          questions, answered
        </div>
        <div className="max-w-[700px] flex flex-col">
          {FAQ.map((item, i) => (
            <FaqItem
              key={item.q}
              q={item.q}
              a={item.a}
              open={openFaq === i}
              onToggle={() => setOpenFaq(o => (o === i ? null : i))}
            />
          ))}
        </div>
      </section>

      {/* closing CTA */}
      <section className="px-12 py-24 border-t border-line">
        <div className="font-serif text-[36px] leading-snug italic max-w-[600px] mb-8">
          &ldquo;What is asking for your attention today?&rdquo;
        </div>
        <AuthCta signedInLabel="Start a conversation →" signedOutLabel="Start a conversation →" />
      </section>

      {/* footer */}
      <footer className="px-12 py-9 border-t border-line flex items-center justify-between flex-wrap gap-4">
        <div className="flex items-center gap-6">
          <Logo size={17} />
          <span className="font-mono text-[12px] text-muted">
            an AI wisdom companion · built on the world&rsquo;s contemplative traditions
          </span>
        </div>
        <div className="flex items-center gap-6 font-mono text-[12px] text-muted">
          <a href="mailto:ananthanarayanan431@gmail.com" className="hover:text-ink transition-colors">
            ananthanarayanan431@gmail.com
          </a>
          <Link href="/home" className="hover:text-ink transition-colors">
            Enter the app →
          </Link>
        </div>
      </footer>
    </div>
  );
}
