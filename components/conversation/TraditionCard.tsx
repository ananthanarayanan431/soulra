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
