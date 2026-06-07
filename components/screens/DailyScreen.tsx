"use client";
import { useState } from "react";
import { Sidebar } from "@/components/layout";
import type { PracticeArc, PracticeDay } from "@/lib/api";
import { DailyClient } from "./DailyClient";

function DayCard({ day, active, onClick }: { day: PracticeDay; active: boolean; onClick: () => void }) {
  const cardClass =
    day.state === "today"
      ? "border-[1.5px] border-ink bg-paper"
      : day.state === "done"
        ? "border border-line bg-paper-alt"
        : "border border-line bg-transparent";

  return (
    <button
      onClick={onClick}
      className={[
        cardClass,
        "rounded-lg p-3 h-[110px] flex flex-col justify-between text-left w-full transition-shadow cursor-pointer",
        active ? "ring-2 ring-ink ring-offset-2 ring-offset-paper" : "hover:border-ink/40",
      ].join(" ")}
    >
      <div className="flex justify-between items-center">
        <span className="font-mono text-[10px] text-muted tracking-wide">{day.day_label}</span>
        <span className="font-mono text-[11px] text-accent">
          {day.state === "done" ? "✓" : day.state === "today" ? "●" : ""}
        </span>
      </div>
      <div className={`font-serif text-[13px] leading-tight italic ${day.state === "future" ? "text-muted" : "text-ink"}`}>
        {day.task_title}
      </div>
    </button>
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
  const [selectedDayNumber, setSelectedDayNumber] = useState(arc?.current_day ?? 1);

  if (!arc) return <EmptyState />;

  const selectedIndex = arc.days.findIndex(d => d.day_number === selectedDayNumber);
  const selectedDay = arc.days[selectedIndex] ?? arc.days[arc.current_day - 1];
  const currentIndex = arc.days.findIndex(d => d.day_number === selectedDay.day_number);
  const prevDay = currentIndex > 0 ? arc.days[currentIndex - 1] : null;
  const nextDay = currentIndex < arc.days.length - 1 ? arc.days[currentIndex + 1] : null;

  const statusLabel =
    selectedDay.state === "today" ? "today" : selectedDay.state === "done" ? "completed" : "upcoming";

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
        <div className="grid grid-cols-7 gap-2 mb-5">
          {arc.days.map(day => (
            <DayCard
              key={day.day_number}
              day={day}
              active={day.day_number === selectedDay.day_number}
              onClick={() => setSelectedDayNumber(day.day_number)}
            />
          ))}
        </div>

        {/* day navigation */}
        <div className="flex items-center justify-between mb-3 px-1">
          <button
            onClick={() => prevDay && setSelectedDayNumber(prevDay.day_number)}
            disabled={!prevDay}
            className="font-mono text-[11px] text-muted hover:text-ink disabled:opacity-0 transition-colors min-w-[90px] text-left"
          >
            {prevDay ? `‹ ${prevDay.day_label}` : ""}
          </button>
          <span className="font-mono text-[10px] text-muted uppercase tracking-widest">
            {selectedDay.day_label} &middot; day {selectedDay.day_number} of {arc.days.length} &middot; {statusLabel}
          </span>
          <button
            onClick={() => nextDay && setSelectedDayNumber(nextDay.day_number)}
            disabled={!nextDay}
            className="font-mono text-[11px] text-muted hover:text-ink disabled:opacity-0 transition-colors min-w-[90px] text-right"
          >
            {nextDay ? `${nextDay.day_label} ›` : ""}
          </button>
        </div>

        {/* interactive morning + evening cards */}
        <DailyClient
          key={selectedDay.day_number}
          arcId={arc.id}
          dayNumber={selectedDay.day_number}
          dayLabel={selectedDay.day_label}
          isToday={selectedDay.state === "today"}
          morningQuote={selectedDay.morning_quote}
          morningAuthor={selectedDay.morning_author}
          morningCitation={selectedDay.morning_citation}
          morningAnalysis={selectedDay.morning_analysis}
          eveningPrompt={selectedDay.evening_prompt}
          initialReflection={selectedDay.reflection_text ?? ""}
          initialCompleted={selectedDay.completed}
        />

        {/* not-a-streak note */}
        <div className="border border-line rounded-lg px-4 py-3.5 bg-paper-alt font-mono text-[11px] text-muted leading-relaxed mt-6">
          this is intentionally not a streak. you can miss a day. the thread holds.
        </div>
      </div>
    </div>
  );
}
