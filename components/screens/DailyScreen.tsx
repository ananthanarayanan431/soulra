"use client";
import { useState } from "react";
import { Sidebar } from "@/components/layout";
import { Button } from "@/components/ui";

const DAYS = [
  { d: "Mon", state: "done", t: "Notice the moment of yes" },
  { d: "Tue", state: "done", t: "Read Meditations VI" },
  { d: "Wed", state: "done", t: "Sit with the resistance" },
  { d: "Thu", state: "today", t: "Pause for one breath" },
  { d: "Fri", state: "future", t: "Decline one small thing" },
  { d: "Sat", state: "future", t: "Notice what felt lighter" },
  { d: "Sun", state: "future", t: "Reflection & integration" },
] as const;

type DayState = "done" | "today" | "future";

export function DailyScreen() {
  const [reflection, setReflection] = useState(
    "Once, when Marcus asked if I could lead the syncs next week. I didn't say yes immediately. I said “let me check tonight.” It felt unfamiliar."
  );

  function dayCardClass(state: DayState) {
    if (state === "today") return "border-[1.5px] border-ink bg-paper";
    if (state === "done") return "border border-line bg-paper-alt";
    return "border border-line bg-transparent";
  }

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
              <em className="text-accent">refusing well</em>
            </div>
          </div>
          <span className="font-mono text-[11px] text-muted">4 days into a 7-day arc</span>
        </div>

        {/* week arc grid */}
        <div className="grid grid-cols-7 gap-2 mb-7">
          {DAYS.map((day, i) => (
            <div
              key={i}
              className={`${dayCardClass(day.state)} rounded-lg p-3 h-[110px] flex flex-col justify-between`}
            >
              <div className="flex justify-between items-center">
                <span className="font-mono text-[10px] text-muted tracking-wide">{day.d}</span>
                <span className="font-mono text-[11px] text-accent">
                  {day.state === "done" ? "✓" : day.state === "today" ? "●" : ""}
                </span>
              </div>
              <div
                className={`font-serif text-[13px] leading-tight italic ${
                  day.state === "future" ? "text-muted" : "text-ink"
                }`}
              >
                {day.t}
              </div>
            </div>
          ))}
        </div>

        {/* today + reflection */}
        <div className="grid grid-cols-[1.4fr_1fr] gap-4 mb-6">
          {/* morning lesson */}
          <div className="border-[1.5px] border-ink rounded-xl p-6 bg-paper">
            <div className="font-mono text-[10px] text-muted uppercase tracking-widest mb-2">
              morning &middot; 8:00am
            </div>
            <div className="font-serif text-[24px] leading-[1.35] italic">
              &ldquo;You always own the option of having no opinion.&rdquo;
            </div>
            <div className="font-mono text-[10px] text-accent mt-2">
              &darr; Marcus Aurelius &middot; Meditations 6.13
            </div>
            <div className="text-[13px] leading-[1.7] text-muted mt-3.5">
              Today&rsquo;s only practice: pause for one breath before answering the next request.
            </div>
            <div className="flex gap-2 mt-5">
              <Button small primary>I&rsquo;ll carry this today</Button>
              <Button small>Read the full passage &#8599;</Button>
              <span className="flex-1" />
              <Button small>&#9671; Save</Button>
            </div>
          </div>

          {/* evening reflection */}
          <div className="border-[1.5px] border-dashed border-ink rounded-xl p-6 bg-paper-alt">
            <div className="font-mono text-[10px] text-muted uppercase tracking-widest mb-2">
              evening &middot; 8:00pm reflection
            </div>
            <div className="font-serif text-[18px] leading-[1.4] italic">
              Did the space between request and answer appear today, even once? What did you find in
              it?
            </div>
            <div className="mt-3.5 border border-line rounded-md p-3 bg-paper min-h-[100px]">
              <div className="font-mono text-[10px] text-muted mb-1.5">your reflection</div>
              <textarea
                className="w-full bg-transparent resize-none outline-none text-[13px] leading-[1.6] text-muted italic"
                rows={4}
                value={reflection}
                onChange={e => setReflection(e.target.value)}
              />
            </div>
            <div className="flex gap-2 mt-3.5">
              <Button small>Save reflection</Button>
              <Button small>Skip tonight</Button>
            </div>
          </div>
        </div>

        {/* not-a-streak note */}
        <div className="border border-line rounded-lg px-4 py-3.5 bg-paper-alt font-mono text-[11px] text-muted leading-relaxed">
          this is intentionally not a streak. you can miss a day. the thread holds.
        </div>
      </div>
    </div>
  );
}
