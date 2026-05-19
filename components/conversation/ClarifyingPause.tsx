// components/conversation/ClarifyingPause.tsx
"use client";
import { useState } from "react";
import { Chip } from "@/components/ui";

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
