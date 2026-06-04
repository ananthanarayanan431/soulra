"use client";
import { useState } from "react";
import { Sidebar } from "@/components/layout";
import { Button, Chip, Input } from "@/components/ui";

const TRADITIONS = [
  {
    tradition: "Stoic",
    author: "Marcus Aurelius",
    quote: "“You always own the option of having no opinion. There is never any need to get worked up or to trouble your soul about things you can’t control.”",
    analysis:
      "The Stoic move here is to notice that the request comes from outside but the yes comes from within. The pressure feels external; the agreement is yours. That distinction is where freedom begins.",
    citation: "Meditations · Book 6, 13 — translated by Hays (2002)",
    preview: null,
  },
  {
    tradition: "Vedanta",
    author: "Bhagavad Gita",
    quote: "“Let right deeds be thy motive, not the fruit which comes from them.”",
    analysis:
      "What if the yes is a way of trying to secure something — approval, belonging, identity? Krishna’s teaching is that any work done to secure those things will resent itself.",
    citation: "Bhagavad Gita · Chapter 2, 47 — trans. Easwaran (2007)",
    preview: "On action without attachment to its fruit…",
  },
  {
    tradition: "Buddhist",
    author: "Pema Chödrön",
    quote: "“When things are shaky and nothing is working, we might realize that we are on the verge of something.”",
    analysis:
      "What if the resistance is the teacher? Stay close to the discomfort, don’t run. The “yes” beneath the yes is asking to be seen.",
    citation: "When Things Fall Apart · Ch. 9",
    preview: "The “yes” beneath the yes — a closer look at the resistance itself…",
  },
];

const STEPS = [
  {
    n: "01",
    title: "Notice the moment of yes",
    body: "When the next request arrives, pause for the length of one breath before answering. That is the only practice today.",
  },
  {
    n: "02",
    title: "Name what you actually want",
    body: "Write one sentence: ‘What I would say if there were no consequence is ___.’ Don’t act on it. Just see it.",
  },
  {
    n: "03",
    title: "Say a small, true no",
    body: "Decline one small, low-stakes request this week. Keep it warm and brief: ‘Not this one — thank you for asking.’",
  },
];

export function ConversationScreen() {
  const [expanded, setExpanded] = useState(new Set([0]));
  const [committed, setCommitted] = useState(new Set<number>());
  const [reply, setReply] = useState("");

  function toggle(i: number) {
    setExpanded(prev => {
      const next = new Set(prev);
      next.has(i) ? next.delete(i) : next.add(i);
      return next;
    });
  }

  function toggleCommit(i: number) {
    setCommitted(prev => {
      const next = new Set(prev);
      next.has(i) ? next.delete(i) : next.add(i);
      return next;
    });
  }

  return (
    <div className="flex h-screen bg-paper overflow-hidden">
      <Sidebar />

      <div className="flex-1 flex flex-col overflow-hidden">
        {/* top bar */}
        <div className="px-9 py-4 border-b border-line flex items-center justify-between flex-shrink-0">
          <div>
            <div className="font-serif text-[16px] font-medium">Saying yes I don&rsquo;t mean</div>
            <div className="font-mono text-[10px] text-muted mt-0.5">
              started 2 min ago &middot; 3 traditions consulted
            </div>
          </div>
          <div className="flex gap-2">
            <Button small>&#9671; Save to journal</Button>
            <Button small>&#8943;</Button>
          </div>
        </div>

        {/* conversation thread */}
        <div className="flex-1 overflow-auto px-9 py-8 flex flex-col gap-7 max-w-[820px] self-center w-full">

          {/* user bubble */}
          <div className="self-end max-w-[520px] px-4 py-3.5 bg-paper-alt border border-line rounded-[14px_14px_2px_14px] text-[14px] leading-relaxed">
            I keep saying yes to projects I don&rsquo;t really want to do, and then resenting myself
            for it. I don&rsquo;t know how to stop.
          </div>

          {/* clarifying pause */}
          <div className="flex gap-3.5">
            <div className="w-8 h-8 rounded-full border-[1.5px] border-ink flex items-center justify-center font-serif text-[14px] flex-shrink-0">
              S
            </div>
            <div className="flex-1">
              <div className="font-mono text-[10px] text-muted uppercase tracking-wide mb-1.5">
                Soulra &middot; pausing to understand
              </div>
              <div className="font-serif text-[19px] leading-[1.5] italic">
                Before I draw on the traditions &mdash; is this most about the work itself, the
                people you&rsquo;re saying yes to, or something inside you that finds it hard to
                refuse?
              </div>
              <div className="flex flex-wrap gap-2 mt-3.5">
                <Chip>The work</Chip>
                <Chip>The people</Chip>
                <Chip active>Something inside me</Chip>
                <Chip>It&rsquo;s all three</Chip>
              </div>
              <div className="font-mono text-[10px] text-muted mt-2">&hellip;or just type a longer answer</div>
            </div>
          </div>

          {/* Soulra response */}
          <div className="flex gap-3.5">
            <div className="w-8 flex-shrink-0" />
            <div className="flex-1 flex flex-col gap-4">
              <p className="text-[14px] leading-[1.7] max-w-[640px]">
                Thank you. What you&rsquo;re describing &mdash; the inability to refuse &mdash; has
                been examined carefully across several traditions. Here are three perspectives, each
                rooted in its own lineage. They don&rsquo;t say the same thing, and that is the
                point.
              </p>

              {/* tradition cards */}
              {TRADITIONS.map((t, i) =>
                expanded.has(i) ? (
                  <button
                    key={i}
                    type="button"
                    onClick={() => toggle(i)}
                    className="w-full text-left border-[1.5px] border-ink rounded-xl p-5 bg-paper hover:bg-paper-alt transition-colors"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-mono text-[10px] text-accent uppercase tracking-widest">
                        {t.tradition} &middot; {t.author}
                      </span>
                      <span className="font-mono text-[10px] text-muted">
                        {i + 1} of {TRADITIONS.length}
                      </span>
                    </div>
                    <div className="font-serif text-[22px] leading-[1.35] italic">{t.quote}</div>
                    <div className="text-[13px] leading-[1.7] mt-3 text-muted">{t.analysis}</div>
                    <div className="mt-3.5 flex items-center gap-2 font-mono text-[10px] text-accent pt-2.5 border-t border-dashed border-line">
                      <span>&darr;</span>
                      <span>{t.citation}</span>
                      <span className="ml-auto text-muted">tap to read original &#8599;</span>
                    </div>
                  </button>
                ) : (
                  <button
                    key={i}
                    onClick={() => toggle(i)}
                    className="w-full border-[1.5px] border-line rounded-xl p-4 bg-paper-alt text-left cursor-pointer hover:border-ink transition-colors"
                  >
                    <div className="flex items-center justify-between gap-4">
                      <div>
                        <div className="font-mono text-[10px] text-accent uppercase tracking-widest mb-1">
                          {t.tradition} &middot; {t.author}
                        </div>
                        <div className="font-serif text-[16px] italic">{t.preview}</div>
                      </div>
                      <span className="font-mono text-[11px] text-muted flex-shrink-0">
                        {i + 1} of {TRADITIONS.length} &middot; expand &#8595;
                      </span>
                    </div>
                  </button>
                )
              )}

              {/* action plan */}
              <div className="border-[1.5px] border-ink rounded-xl bg-ink text-paper p-6 mt-2">
                <div className="font-mono text-[10px] text-accent-soft uppercase tracking-widest mb-1">
                  What you can do today
                </div>
                <div className="font-serif text-[22px] font-medium mb-5">
                  Three steps. Pick the one you&rsquo;ll try.
                </div>

                <div className="flex flex-col">
                  {STEPS.map((s, i) => (
                    <div
                      key={i}
                      className={`flex gap-3.5 py-3 ${i ? "border-t border-[#3a352d]" : ""}`}
                    >
                      <button
                        onClick={() => toggleCommit(i)}
                        className={`w-[22px] h-[22px] border-[1.5px] border-accent-soft rounded-[4px] flex-shrink-0 mt-0.5 flex items-center justify-center text-[11px] transition-colors ${
                          committed.has(i)
                            ? "bg-accent-soft text-ink"
                            : "bg-transparent text-accent-soft"
                        }`}
                      >
                        {committed.has(i) ? "✓" : ""}
                      </button>
                      <div className="flex-1">
                        <div className="font-mono text-[10px] text-accent-soft tracking-wide">
                          {s.n}
                        </div>
                        <div className="text-[14px] font-medium mt-0.5">{s.title}</div>
                        <div className="text-[13px] text-[#cdc6b8] leading-[1.6] mt-1">{s.body}</div>
                      </div>
                    </div>
                  ))}
                </div>

                <div className="flex gap-2 mt-4 pt-3.5 border-t border-[#3a352d] flex-wrap">
                  <button className="text-xs border border-accent-soft text-accent-soft rounded-full px-3 py-1.5 hover:bg-white/5 transition-colors">
                    I&rsquo;ll try one of these
                  </button>
                  <button className="text-xs border border-[#3a352d] text-accent-soft rounded-full px-3 py-1.5 hover:bg-white/5 transition-colors">
                    Suggest different steps
                  </button>
                  <span className="flex-1" />
                  <button className="text-xs border border-accent-soft text-accent-soft rounded-full px-3 py-1.5 hover:bg-white/5 transition-colors">
                    &#9671; Save to journal
                  </button>
                </div>
              </div>

              {/* response footer */}
              <div className="flex justify-between items-center font-mono text-[10px] text-muted pt-1">
                <span>3 sources &middot; 0 paraphrases &middot; grounded response</span>
                <span>was this grounded? &middot; &#128077; &middot; &#128078;</span>
              </div>
            </div>
          </div>
        </div>

        {/* input bar */}
        <div className="px-9 pb-6 pt-4 border-t border-line flex-shrink-0">
          <div className="max-w-[820px] mx-auto">
            <Input
              placeholder="Reply, or ask a follow-up&hellip;"
              value={reply}
              onChange={setReply}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
