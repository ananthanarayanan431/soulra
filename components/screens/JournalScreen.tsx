"use client";
import { useState } from "react";
import { Sidebar } from "@/components/layout";
import { Button, Chip, Squiggle } from "@/components/ui";

const TAGS = [
  { name: "all", count: 12 },
  { name: "career", count: 5 },
  { name: "relationships", count: 3 },
  { name: "grief", count: 1 },
  { name: "identity", count: 2 },
  { name: "practice", count: 4 },
];

const TRADITION_COUNTS = [
  { name: "Stoic", count: 5 },
  { name: "Vedanta", count: 4 },
  { name: "Buddhist", count: 3 },
];

const LESSONS = [
  {
    date: "Apr 28",
    text: "Three small things to refuse warmly.",
    source: "Stoic · Marcus Aurelius · Meditations 6.13",
    tags: ["career", "practice"],
    applied: true,
  },
  {
    date: "Apr 21",
    text: "Action without attachment to the fruit.",
    source: "Vedanta · Bhagavad Gita 2.47",
    tags: ["career"],
    applied: false,
  },
  {
    date: "Apr 18",
    text: "What if the resistance itself is the teacher?",
    source: "Buddhist · Pema Chödrön · When Things Fall Apart",
    tags: ["identity"],
    applied: true,
  },
  {
    date: "Apr 11",
    text: "On grief: a guest you stop trying to evict.",
    source: "Sufi · Rumi · The Guest House",
    tags: ["grief"],
    applied: false,
  },
  {
    date: "Apr 04",
    text: "The disquiet that returns is asking to be heard.",
    source: "Christian mystics · Thomas à Kempis",
    tags: ["identity"],
    applied: false,
  },
];

function EmptyState() {
  return (
    <div className="flex-1 flex flex-col overflow-auto px-[60px]">
      <div className="pt-[60px] pb-[30px] border-b border-line-soft">
        <div className="font-mono text-[10px] text-muted uppercase tracking-widest">your journal</div>
        <div className="font-serif text-[44px] leading-tight mt-2 italic">
          A place for wisdom
          <br />
          that has met you.
        </div>
        <Squiggle width={140} className="mt-4" />
      </div>

      <div className="grid grid-cols-2 gap-[60px] pt-10 pb-[60px]">
        <div>
          <p className="text-[15px] leading-[1.7] text-ink max-w-[460px]">
            Most chat apps treat saved messages like a graveyard. This isn&rsquo;t that.
            <br />
            <br />
            Your journal is the small library of teachings that, for whatever reason, stayed with
            you. A few weeks from now, Soulra will quietly bring one back &mdash; not to remind you
            of an answer, but to ask whether it has shown up.
          </p>

          <div className="mt-8 flex flex-col gap-3.5">
            {[
              ["◇", "Save anything that resonates", "Tap the bookmark on any lesson."],
              ["◯", "Tag by season of life", "Career, grief, identity — your own labels work too."],
              ["⤴", "Mark when it shows up", "The lesson lived is worth more than the lesson read."],
            ].map(([icon, title, body]) => (
              <div key={title} className="flex gap-3.5 items-start">
                <span className="font-mono text-[16px] text-accent w-[18px] mt-0.5 flex-shrink-0">
                  {icon}
                </span>
                <div>
                  <div className="font-serif text-[17px] leading-tight">{title}</div>
                  <div className="text-[13px] text-muted mt-0.5">{body}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div>
          <div className="font-mono text-[10px] text-muted uppercase tracking-widest mb-3.5">
            a starting place &mdash; your first saved lesson
          </div>
          <div className="border-[1.5px] border-ink rounded-xl bg-paper-alt p-6">
            <div className="font-mono text-[10px] text-accent uppercase tracking-widest mb-2">
              Stoic &middot; Epictetus
            </div>
            <div className="font-serif text-[22px] leading-[1.4] italic">
              &ldquo;It is not what happens to you, but how you react to it that matters.&rdquo;
            </div>
            <div className="text-[13px] text-muted mt-3.5 leading-[1.6]">
              We&rsquo;ve placed one teaching here to begin. You don&rsquo;t have to keep it. When
              something resonates more, it can take its place.
            </div>
            <div className="flex gap-2.5 mt-4 pt-3.5 border-t border-dashed border-line items-center">
              <Button small primary>Keep this one</Button>
              <Button small>Choose another &rarr;</Button>
              <span className="flex-1" />
              <span className="font-mono text-[10px] text-muted">Discourses &middot; 1.1.7</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export function JournalScreen({ empty = false }: { empty?: boolean }) {
  const [activeTag, setActiveTag] = useState("all");

  const filtered =
    activeTag === "all" ? LESSONS : LESSONS.filter(l => l.tags.includes(activeTag));

  if (empty) return (
    <div className="flex h-screen bg-paper overflow-hidden">
      <Sidebar />
      <EmptyState />
    </div>
  );

  return (
    <div className="flex h-screen bg-paper overflow-hidden">
      <Sidebar />

      <div className="flex-1 flex flex-col overflow-hidden">
        {/* header */}
        <div className="px-10 pt-7 pb-5 border-b border-line flex items-end justify-between flex-shrink-0">
          <div>
            <div className="font-mono text-[10px] text-muted uppercase tracking-widest">
              your journal
            </div>
            <div className="font-serif text-[36px] leading-tight mt-1">Wisdom you&rsquo;ve kept</div>
            <div className="text-[13px] text-muted mt-1.5">
              12 lessons &middot; 3 applied this month &middot; last revisit 4 days ago
            </div>
          </div>
          <div className="flex gap-2">
            <Button small>&#8599; Export PDF</Button>
            <Button small>+ Add a private note</Button>
          </div>
        </div>

        <div className="flex-1 flex overflow-hidden">
          {/* tag rail */}
          <div className="w-[220px] px-6 py-6 border-r border-line flex flex-col gap-5 flex-shrink-0">
            <div>
              <div className="font-mono text-[10px] text-muted uppercase tracking-widest mb-2.5">
                tags
              </div>
              <div className="flex flex-col gap-1.5">
                {TAGS.map(({ name, count }) => (
                  <button
                    key={name}
                    onClick={() => setActiveTag(name)}
                    className={`flex justify-between items-center text-[13px] py-1 transition-colors text-left ${
                      activeTag === name ? "text-ink font-medium" : "text-muted hover:text-ink"
                    }`}
                  >
                    <span>{name}</span>
                    <span className="font-mono text-[11px]">{count}</span>
                  </button>
                ))}
              </div>
            </div>

            <div>
              <div className="font-mono text-[10px] text-muted uppercase tracking-widest mb-2.5">
                traditions
              </div>
              <div className="flex flex-col gap-1.5">
                {TRADITION_COUNTS.map(({ name, count }) => (
                  <div
                    key={name}
                    className="flex justify-between items-center text-[13px] text-muted py-1"
                  >
                    <span>{name}</span>
                    <span className="font-mono text-[11px]">{count}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* main list */}
          <div className="flex-1 overflow-auto px-9 py-6">
            {/* revisit nudge */}
            <div className="border-[1.5px] border-ink rounded-xl p-5 flex gap-4 bg-paper-alt mb-6">
              <div className="flex-1">
                <div className="font-mono text-[10px] text-accent uppercase tracking-widest mb-1">
                  a lesson worth revisiting
                </div>
                <div className="font-serif text-[22px] leading-[1.35] italic">
                  &ldquo;You always own the option of having no opinion.&rdquo;
                </div>
                <div className="font-mono text-[11px] text-muted mt-2">
                  saved 11 days ago &middot; Stoic &middot; Meditations 6.13
                </div>
              </div>
              <div className="flex flex-col gap-2 items-end flex-shrink-0">
                <Button small primary>Open</Button>
                <span className="font-mono text-[10px] text-muted">has it shown up?</span>
              </div>
            </div>

            {/* lessons list */}
            <div className="border border-line rounded-xl overflow-hidden">
              {filtered.map((row, i) => (
                <div
                  key={i}
                  className={`flex items-start gap-4 px-5 py-4 ${
                    i ? "border-t border-line-soft" : ""
                  }`}
                >
                  <span
                    className={`w-[18px] h-[18px] border-[1.5px] border-ink rounded-[4px] mt-1 flex-shrink-0 flex items-center justify-center text-[11px] ${
                      row.applied ? "bg-ink text-paper" : "bg-transparent"
                    }`}
                  >
                    {row.applied ? "✓" : ""}
                  </span>
                  <div className="flex-1">
                    <div className="font-serif text-[17px] leading-[1.4]">{row.text}</div>
                    <div className="font-mono text-[10px] text-accent mt-1.5 tracking-wide">
                      &darr; {row.source}
                    </div>
                    <div className="flex gap-1.5 mt-2">
                      {row.tags.map(t => (
                        <Chip key={t} className="text-[10px] px-2 py-0.5">
                          {t}
                        </Chip>
                      ))}
                    </div>
                  </div>
                  <div className="font-mono text-[10px] text-muted mt-1 flex-shrink-0">
                    {row.date}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
