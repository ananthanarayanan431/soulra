"use client";
import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { Sidebar } from "@/components/layout";
import { Button, Chip } from "@/components/ui";
import { saveJournalEntry, patchJournalEntry, deleteJournalEntry, formatRelativeDate } from "@/lib/api";
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
    <div className="border-[1.5px] border-ink rounded-xl p-6 flex gap-6 bg-paper-alt mb-7">
      <div className="flex-1">
        <div className="font-mono text-[10px] text-accent uppercase tracking-widest mb-2">
          a lesson worth revisiting
        </div>
        <div className="font-serif text-[23px] leading-[1.45] italic">
          &ldquo;{entry.text}&rdquo;
        </div>
        <div className="font-mono text-[11px] text-muted mt-3 leading-relaxed">
          saved {formatRelativeDate(entry.saved_at)}
          {sourceLabel(entry) ? ` · ${sourceLabel(entry)}` : ""}
        </div>
      </div>
      <div className="flex flex-col gap-2.5 items-end justify-center flex-shrink-0 min-w-[150px]">
        <span className="font-mono text-[11px] text-muted">has it shown up?</span>
        <Button small primary onClick={() => onApply(entry.id)}>
          {entry.applied ? "Applied ✓" : "Mark applied"}
        </Button>
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
        className={`flex items-start gap-4 px-6 py-5 group ${hasDetail ? "cursor-pointer select-none" : ""}`}
        onClick={hasDetail ? () => setOpen(o => !o) : undefined}
      >
        <button
          onClick={e => { e.stopPropagation(); onToggleApplied(entry.id, entry.applied); }}
          className={`w-[20px] h-[20px] border-[1.5px] border-ink rounded-[5px] mt-1 flex-shrink-0 flex items-center justify-center text-[12px] transition-colors ${
            entry.applied ? "bg-ink text-paper" : "bg-transparent hover:bg-ink/10"
          }`}
        >
          {entry.applied ? "✓" : ""}
        </button>

        <div className="flex-1 min-w-0">
          <div className="font-serif text-[18px] leading-[1.5]">{entry.text}</div>
          {sourceLabel(entry) && (
            <div className="font-mono text-[11px] text-ink/60 mt-2 tracking-wide leading-relaxed">
              &darr; {sourceLabel(entry)}
            </div>
          )}
        </div>

        <div className="flex items-center gap-3.5 flex-shrink-0">
          <div className="font-mono text-[11px] text-muted mt-1.5 whitespace-nowrap">
            {formatSavedDate(entry.saved_at)}
          </div>
          {hasDetail && (
            <span className="font-mono text-[12px] text-muted mt-1.5 transition-transform duration-200" style={{ display: "inline-block", transform: open ? "rotate(90deg)" : "rotate(0deg)" }}>
              ›
            </span>
          )}
          <button
            onClick={e => { e.stopPropagation(); onDelete(entry.id); }}
            className="opacity-0 group-hover:opacity-100 font-mono text-[11px] text-muted hover:text-red-700 transition-opacity mt-1.5"
          >
            ✕
          </button>
        </div>
      </div>

      {/* expanded detail panel */}
      {open && hasDetail && (
        <div className="px-6 pb-6 ml-[44px] flex flex-col gap-4">
          {entry.quote && (
            <blockquote className="font-serif text-[20px] leading-[1.6] italic border-l-2 border-ink pl-5 text-ink">
              &ldquo;{entry.quote}&rdquo;
            </blockquote>
          )}
          {entry.analysis && (
            <p className="text-[14px] leading-[1.8] text-ink/70 max-w-[640px]">
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
  const [showNoteForm, setShowNoteForm] = useState(false);
  const [noteText, setNoteText] = useState("");
  const [noteSaving, setNoteSaving] = useState(false);

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

  async function handleSaveNote() {
    const trimmed = noteText.trim();
    if (!trimmed) return;
    setNoteSaving(true);
    const entry = await saveJournalEntry({ text: trimmed });
    setNoteSaving(false);
    if (entry) {
      setNoteText("");
      setShowNoteForm(false);
      router.refresh();
    }
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
            <div className="text-[14px] text-muted mt-2 leading-relaxed">{statsLine}</div>
          </div>
          <div className="flex gap-2">
            <Button small onClick={() => { setShowNoteForm(v => !v); setNoteText(""); }}>
              {showNoteForm ? "Cancel" : "+ Add a private note"}
            </Button>
          </div>
        </div>

        {showNoteForm && (
          <div className="px-10 py-4 border-b border-line bg-paper-alt flex flex-col gap-3">
            <textarea
              autoFocus
              className="w-full bg-paper border border-line rounded-lg px-4 py-3 text-[14px] leading-[1.7] resize-none outline-none focus:border-ink transition-colors"
              rows={3}
              placeholder="Write a private note…"
              value={noteText}
              onChange={e => setNoteText(e.target.value)}
              onKeyDown={e => {
                if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) handleSaveNote();
              }}
            />
            <div className="flex gap-2 items-center">
              <Button small primary onClick={handleSaveNote} disabled={noteSaving || !noteText.trim()}>
                {noteSaving ? "Saving…" : "Save note"}
              </Button>
              <span className="font-mono text-[10px] text-muted">⌘↵ to save</span>
            </div>
          </div>
        )}

        <div className="flex-1 flex overflow-hidden">
          {/* tag + traditions rail */}
          <div className="w-[230px] px-6 py-7 border-r border-line flex flex-col gap-7 flex-shrink-0 overflow-auto">
            <div>
              <div className="font-mono text-[10px] text-muted uppercase tracking-widest mb-3">tags</div>
              <div className="flex flex-col gap-1">
                {tag_counts.map(({ name, count }) => (
                  <button
                    key={name}
                    onClick={() => setActiveTag(name)}
                    className={`flex justify-between items-center text-[14px] py-1.5 px-2 -mx-2 rounded-md transition-colors text-left ${
                      activeTag === name ? "text-ink font-medium bg-paper" : "text-muted hover:text-ink hover:bg-paper/60"
                    }`}
                  >
                    <span>{name}</span>
                    <span className="font-mono text-[11px] text-muted">{count}</span>
                  </button>
                ))}
              </div>
            </div>

            {tradition_counts.length > 0 && (
              <div>
                <div className="font-mono text-[10px] text-muted uppercase tracking-widest mb-3">
                  traditions
                </div>
                <div className="flex flex-col gap-1">
                  {tradition_counts.map(({ name, count }) => (
                    <div
                      key={name}
                      className="flex justify-between items-center text-[14px] text-muted py-1.5 px-2 -mx-2"
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
