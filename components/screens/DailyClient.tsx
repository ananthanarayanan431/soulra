"use client";
import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui";
import { completeDay, saveReflection, saveJournalEntry } from "@/lib/api";

interface Props {
  arcId: string;
  dayNumber: number;
  morningQuote: string;
  morningAuthor: string;
  morningCitation: string;
  morningAnalysis: string;
  eveningPrompt: string;
  initialReflection: string;
  initialCompleted: boolean;
}

export function DailyClient({
  arcId,
  dayNumber,
  morningQuote,
  morningAuthor,
  morningCitation,
  morningAnalysis,
  eveningPrompt,
  initialReflection,
  initialCompleted,
}: Props) {
  const router = useRouter();
  const [carried, setCarried] = useState(initialCompleted);
  const [reflection, setReflection] = useState(initialReflection);
  const [saved, setSaved] = useState(false);
  const [journalState, setJournalState] = useState<"idle" | "saving" | "saved">("idle");
  const [, startTransition] = useTransition();

  function handleCarry() {
    setCarried(true);
    startTransition(async () => {
      await completeDay(arcId, dayNumber);
      router.refresh();
    });
  }

  async function handleSaveToJournal() {
    if (journalState !== "idle") return;
    setJournalState("saving");
    try {
      await saveJournalEntry({
        text: morningQuote.slice(0, 120),
        quote: morningQuote,
        author: morningAuthor,
        citation: morningCitation,
        analysis: morningAnalysis,
      });
      setJournalState("saved");
    } catch {
      setJournalState("idle");
    }
  }

  function handleSaveReflection() {
    const trimmed = reflection.trim();
    if (!trimmed) return;
    startTransition(async () => {
      await saveReflection(arcId, dayNumber, trimmed);
      setSaved(true);
    });
  }

  return (
    <div className="grid grid-cols-[1.4fr_1fr] gap-4 mb-6">
      {/* morning lesson */}
      <div className="border-[1.5px] border-ink rounded-xl p-6 bg-paper">
        <div className="font-mono text-[10px] text-muted uppercase tracking-widest mb-2">
          morning &middot; today&rsquo;s practice
        </div>
        <div className="font-serif text-[24px] leading-[1.35] italic">
          &ldquo;{morningQuote}&rdquo;
        </div>
        <div className="font-mono text-[10px] text-accent mt-2">
          &darr; {morningAuthor} &middot; {morningCitation}
        </div>
        <div className="text-[13px] leading-[1.7] text-muted mt-3.5">
          {morningAnalysis}
        </div>
        <div className="flex gap-2 mt-5">
          <Button small primary onClick={handleCarry} disabled={carried}>
            {carried ? "Carrying this today ✓" : "I’ll carry this today"}
          </Button>
          <span className="flex-1" />
          <Button small onClick={handleSaveToJournal} disabled={journalState !== "idle"}>
            {journalState === "saving" ? "Saving…" : journalState === "saved" ? "◇ Saved ✓" : "◇ Save"}
          </Button>
        </div>
      </div>

      {/* evening reflection */}
      <div className="border-[1.5px] border-dashed border-ink rounded-xl p-6 bg-paper-alt">
        <div className="font-mono text-[10px] text-muted uppercase tracking-widest mb-2">
          evening &middot; reflection
        </div>
        <div className="font-serif text-[18px] leading-[1.4] italic">
          {eveningPrompt}
        </div>
        <div className="mt-3.5 border border-line rounded-md p-3 bg-paper min-h-[100px]">
          <div className="font-mono text-[10px] text-muted mb-1.5">your reflection</div>
          <textarea
            className="w-full bg-transparent resize-none outline-none text-[13px] leading-[1.6] text-ink italic"
            rows={4}
            value={reflection}
            placeholder="What showed up today?"
            onChange={e => { setReflection(e.target.value); setSaved(false); }}
          />
        </div>
        <div className="flex gap-2 mt-3.5">
          <Button small onClick={handleSaveReflection}>
            {saved ? "Saved ✓" : "Save reflection"}
          </Button>
          <Button small onClick={() => setReflection("")}>Skip tonight</Button>
        </div>
      </div>
    </div>
  );
}
