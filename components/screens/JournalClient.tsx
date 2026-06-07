"use client";
import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { Sidebar } from "@/components/layout";
import { Button, Chip } from "@/components/ui";
import { patchJournalEntry, deleteJournalEntry, formatRelativeDate } from "@/lib/api";
import type { JournalData, JournalEntry } from "@/lib/api";

function formatSavedDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function sourceLabel(entry: JournalEntry): string {
  const parts = [entry.tradition, entry.author, entry.citation].filter(Boolean);
  return parts.join(" · ");
}

function RevisitCard({ entry, onApply }: { entry: JournalEntry; onApply: (id: string) => void }) {
  return (
    <div className="border-[1.5px] border-ink rounded-xl p-5 flex gap-4 bg-paper-alt mb-6">
      <div className="flex-1">
        <div className="font-mono text-[10px] text-accent uppercase tracking-widest mb-1">
          a lesson worth revisiting
        </div>
        <div className="font-serif text-[22px] leading-[1.35] italic">
          &ldquo;{entry.text}&rdquo;
        </div>
        <div className="font-mono text-[11px] text-muted mt-2">
          saved {formatRelativeDate(entry.saved_at)}
          {sourceLabel(entry) ? ` · ${sourceLabel(entry)}` : ""}
        </div>
      </div>
      <div className="flex flex-col gap-2 items-end flex-shrink-0">
        <Button small primary onClick={() => onApply(entry.id)}>
          {entry.applied ? "Applied ✓" : "Mark applied"}
        </Button>
        <span className="font-mono text-[10px] text-muted">has it shown up?</span>
      </div>
    </div>
  );
}

function EntryRow({
  entry,
  onToggleApplied,
  onDelete,
}: {
  entry: JournalEntry;
  onToggleApplied: (id: string, current: boolean) => void;
  onDelete: (id: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const hasDetail = !!(entry.quote || entry.analysis);

  return (
    <div>
      {/* collapsed header row */}
      <div
        className={`flex items-start gap-4 px-5 py-4 group ${hasDetail ? "cursor-pointer select-none" : ""}`}
        onClick={hasDetail ? () => setOpen(o => !o) : undefined}
      >
        <button
          onClick={e => { e.stopPropagation(); onToggleApplied(entry.id, entry.applied); }}
          className={`w-[18px] h-[18px] border-[1.5px] border-ink rounded-[4px] mt-1 flex-shrink-0 flex items-center justify-center text-[11px] transition-colors ${
            entry.applied ? "bg-ink text-paper" : "bg-transparent hover:bg-ink/10"
          }`}
        >
          {entry.applied ? "✓" : ""}
        </button>

        <div className="flex-1 min-w-0">
          <div className="font-serif text-[17px] leading-[1.4]">{entry.text}</div>
          {sourceLabel(entry) && (
            <div className="font-mono text-[10px] text-accent mt-1.5 tracking-wide">
              &darr; {sourceLabel(entry)}
            </div>
          )}
        </div>

        <div className="flex items-center gap-3 flex-shrink-0">
          <div className="font-mono text-[10px] text-muted mt-1">
            {formatSavedDate(entry.saved_at)}
          </div>
          {hasDetail && (
            <span className="font-mono text-[10px] text-muted mt-1 transition-transform duration-200" style={{ display: "inline-block", transform: open ? "rotate(90deg)" : "rotate(0deg)" }}>
              ›
            </span>
          )}
          <button
            onClick={e => { e.stopPropagation(); onDelete(entry.id); }}
            className="opacity-0 group-hover:opacity-100 font-mono text-[10px] text-muted hover:text-red-700 transition-opacity mt-1"
          >
            ✕
          </button>
        </div>
      </div>

      {/* expanded detail panel */}
      {open && hasDetail && (
        <div className="px-5 pb-5 ml-[42px] flex flex-col gap-4">
          {entry.quote && (
            <blockquote className="font-serif text-[20px] leading-[1.5] italic border-l-2 border-ink pl-4 text-ink">
              &ldquo;{entry.quote}&rdquo;
            </blockquote>
          )}
          {entry.analysis && (
            <p className="text-[13px] leading-[1.75] text-muted max-w-[620px]">
              {entry.analysis}
            </p>
          )}
          {entry.tags.length > 0 && (
            <div className="flex gap-1.5 flex-wrap">
              {entry.tags.map(t => (
                <Chip key={t} className="text-[10px] px-2 py-0.5">{t}</Chip>
              ))}
            </div>
          )}
          <div className="flex gap-3 items-center">
            <button
              onClick={() => onToggleApplied(entry.id, entry.applied)}
              className={`font-mono text-[10px] px-3 py-1.5 rounded-full border transition-colors ${
                entry.applied
                  ? "border-ink bg-ink text-paper"
                  : "border-line text-muted hover:border-ink hover:text-ink"
              }`}
            >
              {entry.applied ? "Applied ✓" : "Mark applied"}
            </button>
            {entry.applied_at && (
              <span className="font-mono text-[10px] text-muted">
                applied {formatRelativeDate(entry.applied_at!)}
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export function JournalClient({ initialData }: { initialData: JournalData }) {
  const router = useRouter();
  const [activeTag, setActiveTag] = useState("all");
  const [data, setData] = useState(initialData);
  const [, startTransition] = useTransition();

  const filtered = activeTag === "all"
    ? data.entries
    : data.entries.filter(e => e.tags.includes(activeTag));

  function handleToggleApplied(id: string, current: boolean) {
    setData(d => ({
      ...d,
      entries: d.entries.map(e =>
        e.id === id ? { ...e, applied: !current, applied_at: !current ? new Date().toISOString() : null } : e
      ),
    }));
    startTransition(async () => {
      await patchJournalEntry(id, { applied: !current });
      router.refresh();
    });
  }

  function handleDelete(id: string) {
    setData(d => ({ ...d, entries: d.entries.filter(e => e.id !== id) }));
    startTransition(async () => {
      await deleteJournalEntry(id);
      router.refresh();
    });
  }

  const { stats, tag_counts, tradition_counts, revisit } = data;

  const statsLine = [
    `${stats.total} lesson${stats.total !== 1 ? "s" : ""}`,
    stats.applied_this_month > 0 ? `${stats.applied_this_month} applied this month` : null,
    stats.last_applied_days_ago !== null ? `last applied ${stats.last_applied_days_ago} days ago` : null,
  ].filter(Boolean).join(" · ");

  return (
    <div className="flex h-screen bg-paper overflow-hidden">
      <Sidebar />

      <div className="flex-1 flex flex-col overflow-hidden">
        {/* header */}
        <div className="px-10 pt-7 pb-5 border-b border-line flex items-end justify-between flex-shrink-0">
          <div>
            <div className="font-mono text-[10px] text-muted uppercase tracking-widest">your journal</div>
            <div className="font-serif text-[36px] leading-tight mt-1">Wisdom you&rsquo;ve kept</div>
            <div className="text-[13px] text-muted mt-1.5">{statsLine}</div>
          </div>
          <div className="flex gap-2">
            <Button small>+ Add a private note</Button>
          </div>
        </div>

        <div className="flex-1 flex overflow-hidden">
          {/* tag + traditions rail */}
          <div className="w-[220px] px-6 py-6 border-r border-line flex flex-col gap-5 flex-shrink-0 overflow-auto">
            <div>
              <div className="font-mono text-[10px] text-muted uppercase tracking-widest mb-2.5">tags</div>
              <div className="flex flex-col gap-1.5">
                {tag_counts.map(({ name, count }) => (
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

            {tradition_counts.length > 0 && (
              <div>
                <div className="font-mono text-[10px] text-muted uppercase tracking-widest mb-2.5">
                  traditions
                </div>
                <div className="flex flex-col gap-1.5">
                  {tradition_counts.map(({ name, count }) => (
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
            )}
          </div>

          {/* main list */}
          <div className="flex-1 overflow-auto px-9 py-6">
            {revisit && (
              <RevisitCard
                entry={revisit}
                onApply={id => handleToggleApplied(id, revisit.applied)}
              />
            )}

            {filtered.length === 0 ? (
              <div className="font-serif text-[18px] text-muted italic mt-10 text-center">
                No entries{activeTag !== "all" ? ` tagged "${activeTag}"` : ""}.
              </div>
            ) : (
              <div className="border border-line rounded-xl overflow-hidden">
                {filtered.map((entry, i) => (
                  <div key={entry.id} className={i ? "border-t border-line-soft" : ""}>
                    <EntryRow
                      entry={entry}
                      onToggleApplied={handleToggleApplied}
                      onDelete={handleDelete}
                    />
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
