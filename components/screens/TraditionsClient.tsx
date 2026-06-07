"use client";
import { useState, useTransition } from "react";
import { Sidebar } from "@/components/layout";
import { Chip } from "@/components/ui";
import type { TraditionsData } from "@/lib/api";
import { updateTraditionPreferences } from "@/lib/api";

const ERAS = ["all", "ancient", "medieval", "perennial"] as const;

export function TraditionsClient({ initialData }: { initialData: TraditionsData }) {
  const { traditions, total_sources, total_passages } = initialData;

  const [selectedEra, setSelectedEra] = useState<string>("all");
  const [selectedSlugs, setSelectedSlugs] = useState<Set<string>>(
    () => new Set(traditions.filter(t => t.selected).map(t => t.slug))
  );
  const [, startTransition] = useTransition();

  function toggleTradition(slug: string) {
    const next = new Set(selectedSlugs);
    next.has(slug) ? next.delete(slug) : next.add(slug);
    const slugs = Array.from(next);
    setSelectedSlugs(next);
    startTransition(() => { updateTraditionPreferences(slugs); });
  }

  const visible = selectedEra === "all"
    ? traditions
    : traditions.filter(t => t.era === selectedEra);

  const selectedTraditions = traditions.filter(t => selectedSlugs.has(t.slug));

  return (
    <div className="flex h-screen bg-paper overflow-hidden">
      <Sidebar />

      <div className="flex-1 flex flex-col overflow-hidden">
        {/* header */}
        <div className="px-10 pt-7 pb-5 border-b border-line flex-shrink-0">
          <div className="font-mono text-[10px] text-muted uppercase tracking-widest">
            wisdom traditions
          </div>
          <div className="font-serif text-[36px] leading-tight mt-1">
            The voices in your room
          </div>
          <div className="text-[13px] text-muted mt-2 max-w-[540px] leading-relaxed">
            Soulra draws from these lineages when answering your questions. Pick three or more to
            keep in the room — you can always change them.
          </div>
        </div>

        {/* body */}
        <div className="flex-1 overflow-auto px-10 py-7">
          {/* active selection summary */}
          <div className="border-[1.5px] border-ink rounded-xl p-5 bg-paper-alt mb-7 flex items-start justify-between gap-6">
            <div className="flex-1">
              <div className="font-mono text-[10px] text-muted uppercase tracking-widest mb-3">
                your selection · {selectedSlugs.size} of {traditions.length} voices
              </div>
              <div className="flex flex-wrap gap-2">
                {selectedTraditions.map(t => (
                  <span
                    key={t.slug}
                    className="text-[11px] px-2.5 py-1 rounded-full bg-ink text-paper"
                  >
                    {t.name} ×
                  </span>
                ))}
              </div>
            </div>
            <div className="font-mono text-[10px] text-muted leading-relaxed text-right flex-shrink-0">
              {total_sources.toLocaleString()} source texts<br />
              {total_passages.toLocaleString()} passages indexed
            </div>
          </div>

          {/* era filters */}
          <div className="flex gap-2 mb-6">
            <span className="font-mono text-[10px] text-muted self-center mr-1">filter:</span>
            {ERAS.map(era => (
              <Chip key={era} active={era === selectedEra} onClick={() => setSelectedEra(era)}>
                {era}
              </Chip>
            ))}
          </div>

          {/* tradition cards grid */}
          <div className="grid grid-cols-3 gap-3">
            {visible.map(t => {
              const isPicked = selectedSlugs.has(t.slug);
              return (
                <button
                  key={t.slug}
                  type="button"
                  onClick={() => toggleTradition(t.slug)}
                  className={`w-full text-left rounded-xl p-5 transition-all ${
                    isPicked
                      ? "border-[1.5px] border-ink bg-ink text-paper shadow-md"
                      : "border border-line bg-paper hover:border-ink"
                  }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className={`font-serif text-[18px] font-medium ${isPicked ? "text-paper" : "text-ink"}`}>
                        {t.name}
                      </div>
                      <div className={`font-mono text-[9px] mt-1 tracking-wide ${isPicked ? "text-accent-soft" : "text-muted"}`}>
                        {t.origin}
                      </div>
                    </div>
                    <span className={`font-mono text-[13px] flex-shrink-0 mt-0.5 ${isPicked ? "text-accent-soft" : "text-muted"}`}>
                      {isPicked ? "✓" : "+"}
                    </span>
                  </div>
                  <div className={`font-mono text-[10px] mt-3 pt-3 border-t ${isPicked ? "border-[#3a352d] text-accent-soft" : "border-dashed border-line text-muted"}`}>
                    {t.sources} sources &middot; {t.passages.toLocaleString()} passages
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
