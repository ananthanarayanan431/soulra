import { Sidebar } from "@/components/layout";
import type { PracticeArc, PracticeDay } from "@/lib/api";
import { DailyClient } from "./DailyClient";

function DayCard({ day }: { day: PracticeDay }) {
  const cardClass =
    day.state === "today"
      ? "border-[1.5px] border-ink bg-paper"
      : day.state === "done"
        ? "border border-line bg-paper-alt"
        : "border border-line bg-transparent";

  return (
    <div className={`${cardClass} rounded-lg p-3 h-[110px] flex flex-col justify-between`}>
      <div className="flex justify-between items-center">
        <span className="font-mono text-[10px] text-muted tracking-wide">{day.day_label}</span>
        <span className="font-mono text-[11px] text-accent">
          {day.state === "done" ? "✓" : day.state === "today" ? "●" : ""}
        </span>
      </div>
      <div className={`font-serif text-[13px] leading-tight italic ${day.state === "future" ? "text-muted" : "text-ink"}`}>
        {day.task_title}
      </div>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex h-screen bg-paper overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col items-center justify-center gap-3 px-10">
        <div className="font-serif text-[28px] leading-tight text-center max-w-[480px]">
          No active practice yet.
        </div>
        <div className="text-[14px] text-muted text-center max-w-[420px] leading-relaxed">
          Complete a conversation to begin your 7-day practice arc.
        </div>
      </div>
    </div>
  );
}

export function DailyScreen({ arc }: { arc: PracticeArc | null }) {
  if (!arc) return <EmptyState />;

  const today = arc.days.find(d => d.state === "today") ?? arc.days[arc.current_day - 1];

  return (
    <div className="flex h-screen bg-paper overflow-hidden">
      <Sidebar />

      <div className="flex-1 overflow-auto px-10 py-8">
        {/* header */}
        <div className="flex justify-between items-end mb-7">
          <div>
            <div className="font-mono text-[10px] text-muted uppercase tracking-widest">
              your practice &middot; this week
            </div>
            <div className="font-serif text-[32px] leading-tight mt-1">
              The thread you&rsquo;re working with:{" "}
              <em className="text-accent">{arc.theme}</em>
            </div>
          </div>
          <span className="font-mono text-[11px] text-muted">{arc.days_into_arc}</span>
        </div>

        {/* week arc grid */}
        <div className="grid grid-cols-7 gap-2 mb-7">
          {arc.days.map(day => (
            <DayCard key={day.day_number} day={day} />
          ))}
        </div>

        {/* interactive morning + evening cards */}
        {today && (
          <DailyClient
            arcId={arc.id}
            dayNumber={today.day_number}
            morningQuote={today.morning_quote}
            morningAuthor={today.morning_author}
            morningCitation={today.morning_citation}
            morningAnalysis={today.morning_analysis}
            eveningPrompt={today.evening_prompt}
            initialReflection={today.reflection_text ?? ""}
            initialCompleted={today.completed}
          />
        )}

        {/* not-a-streak note */}
        <div className="border border-line rounded-lg px-4 py-3.5 bg-paper-alt font-mono text-[11px] text-muted leading-relaxed mt-6">
          this is intentionally not a streak. you can miss a day. the thread holds.
        </div>
      </div>
    </div>
  );
}
