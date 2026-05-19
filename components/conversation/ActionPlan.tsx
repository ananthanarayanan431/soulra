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
        Three steps. Pick the one you&apos;ll try.
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
          I&apos;ll try one of these
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
