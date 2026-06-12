"use client";
import { useEffect, useState } from "react";
import { Wordmark, Squiggle } from "@/components/ui";

const SLIDES = [
  {
    tag: "an ai wisdom companion",
    quote: "What is asking for your attention today?",
    body: "Soulra draws from Stoic, Vedanta, Buddhist, Sufi and other wisdom lineages — not to hand you a single answer, but to show you how each tradition sees your knot.",
  },
  {
    tag: "many voices, not one verdict",
    quote: "A Stoic and a Sufi won't always agree.",
    body: "Soulra won't paper over that. The disagreement between traditions is often where your own thinking actually begins.",
  },
  {
    tag: "practice, not just insight",
    quote: "A good conversation can fade by the next morning.",
    body: "So every conversation can seed a 7-day practice thread — small, concrete ways to carry what you found into the week ahead.",
  },
];

function AuthShowcase() {
  const slides = [...SLIDES, SLIDES[0]];
  const [index, setIndex] = useState(0);
  const [animate, setAnimate] = useState(true);

  useEffect(() => {
    const interval = setInterval(() => {
      setAnimate(true);
      setIndex(i => i + 1);
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (index === slides.length - 1) {
      const timeout = setTimeout(() => {
        setAnimate(false);
        setIndex(0);
      }, 700);
      return () => clearTimeout(timeout);
    }
  }, [index, slides.length]);

  return (
    <div className="w-full max-w-[440px] overflow-hidden">
      <div
        className={`flex ${animate ? "transition-transform duration-700 ease-in-out" : ""}`}
        style={{ transform: `translateX(-${index * 100}%)` }}
      >
        {slides.map((slide, i) => (
          <div key={i} className="w-full flex-shrink-0 flex flex-col items-center gap-7 text-center">
            <div className="font-mono text-[11px] text-paper/60 uppercase tracking-widest">
              {slide.tag}
            </div>
            <div className="font-serif text-[34px] leading-[1.4] italic">
              &ldquo;{slide.quote}&rdquo;
            </div>
            <Squiggle width={104} className="text-paper/30" />
            <p className="text-[14px] text-paper/60 leading-[1.85]">{slide.body}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

export function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen grid md:grid-cols-2 bg-paper text-ink">
      <div className="flex flex-col items-center justify-center gap-8 px-6 py-16">
        <Wordmark size={22} />
        <div className="w-full max-w-[400px]">{children}</div>
      </div>

      <div className="hidden md:flex items-center justify-center bg-ink text-paper px-12 py-16">
        <AuthShowcase />
      </div>
    </div>
  );
}
