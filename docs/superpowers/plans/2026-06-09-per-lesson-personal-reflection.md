# Per-Lesson Personal Reflection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the global "Add a private note" form with a per-lesson personal reflection textarea that saves to the backend.

**Architecture:** Add a nullable `personal_note` Text column to `JournalEntry`, expose it through the existing PATCH endpoint, and render an inline editable textarea in the expanded entry detail panel. The global note form is removed entirely.

**Tech Stack:** FastAPI + SQLAlchemy (backend), Alembic (migrations), Next.js + TypeScript (frontend)

---

## File Map

| File | Change |
|------|--------|
| `soulra-backend/soulra/models/journal.py` | Add `personal_note` column |
| `soulra-backend/migrations/versions/0005_journal_personal_note.py` | New migration |
| `soulra-backend/soulra/schemas/journal.py` | Add field to `JournalEntryOut` and `PatchJournalEntry` |
| `soulra-backend/soulra/api/v1/journal.py` | Handle `personal_note` in PATCH endpoint |
| `lib/api.ts` | Add `personal_note` to `JournalEntry` interface and `patchJournalEntry` body |
| `components/screens/JournalClient.tsx` | Add per-entry reflection UI, remove global note form |

---

## Task 1: Add `personal_note` column to the DB model

**Files:**
- Modify: `soulra-backend/soulra/models/journal.py`

- [ ] **Step 1: Add the column**

In [soulra-backend/soulra/models/journal.py](soulra-backend/soulra/models/journal.py), add after the `analysis` line:

```python
    personal_note: Mapped[str | None] = mapped_column(Text, nullable=True)
```

Full updated model for reference:
```python
class JournalEntry(Base):
    __tablename__ = "journal_entries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    quote: Mapped[str | None] = mapped_column(Text, nullable=True)
    tradition: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    author: Mapped[str | None] = mapped_column(String(255), nullable=True)
    citation: Mapped[str | None] = mapped_column(String(255), nullable=True)
    analysis: Mapped[str | None] = mapped_column(Text, nullable=True)
    personal_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, server_default="{}")
    applied: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    applied_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    saved_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
```

---

## Task 2: Write and run the Alembic migration

**Files:**
- Create: `soulra-backend/migrations/versions/0005_journal_personal_note.py`

- [ ] **Step 1: Create the migration file**

```python
"""add personal_note to journal_entries

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-09

"""
from alembic import op
import sqlalchemy as sa

revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'journal_entries',
        sa.Column('personal_note', sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('journal_entries', 'personal_note')
```

- [ ] **Step 2: Apply the migration**

```bash
cd soulra-backend
source .venv/bin/activate
DATABASE_URL=<your-db-url> alembic upgrade head
```

Expected: `Running upgrade 0004 -> 0005, add personal_note to journal_entries`

- [ ] **Step 3: Commit**

```bash
git add soulra-backend/soulra/models/journal.py soulra-backend/migrations/versions/0005_journal_personal_note.py
git commit -m "feat: add personal_note column to journal_entries"
```

---

## Task 3: Update backend schemas and PATCH endpoint

**Files:**
- Modify: `soulra-backend/soulra/schemas/journal.py`
- Modify: `soulra-backend/soulra/api/v1/journal.py`

- [ ] **Step 1: Add `personal_note` to `JournalEntryOut`**

In [soulra-backend/soulra/schemas/journal.py](soulra-backend/soulra/schemas/journal.py), update `JournalEntryOut`:

```python
class JournalEntryOut(BaseModel):
    id: uuid.UUID
    text: str
    quote: str | None
    tradition: str | None
    author: str | None
    citation: str | None
    analysis: str | None
    personal_note: str | None
    tags: list[str]
    applied: bool
    applied_at: datetime | None
    saved_at: datetime
    conversation_id: uuid.UUID | None

    model_config = {"from_attributes": True}
```

- [ ] **Step 2: Add `personal_note` to `PatchJournalEntry`**

Update `PatchJournalEntry`:

```python
class PatchJournalEntry(BaseModel):
    applied: bool | None = None
    tags: list[str] | None = None
    personal_note: str | None = None
```

- [ ] **Step 3: Handle `personal_note` in the PATCH endpoint**

In [soulra-backend/soulra/api/v1/journal.py](soulra-backend/soulra/api/v1/journal.py), add to the `patch_journal_entry` handler after the tags block:

```python
    if body.applied is not None:
        row.applied = body.applied
        row.applied_at = datetime.now(timezone.utc) if body.applied else None
    if body.tags is not None:
        row.tags = body.tags
    if body.personal_note is not None:
        row.personal_note = body.personal_note
```

Note: `personal_note` can be set to `""` (empty string) to clear it. If you want `null` clearing, use a sentinel pattern — but for now, passing empty string is sufficient.

- [ ] **Step 4: Verify the server starts without errors**

```bash
cd soulra-backend
source .venv/bin/activate
uvicorn soulra.main:app --reload --port 8000
```

Expected: Server starts, no import errors.

- [ ] **Step 5: Commit**

```bash
git add soulra-backend/soulra/schemas/journal.py soulra-backend/soulra/api/v1/journal.py
git commit -m "feat: expose personal_note in journal schema and PATCH endpoint"
```

---

## Task 4: Update frontend API layer

**Files:**
- Modify: `lib/api.ts`

- [ ] **Step 1: Add `personal_note` to the `JournalEntry` interface**

In [lib/api.ts](lib/api.ts), update the `JournalEntry` interface:

```typescript
export interface JournalEntry {
  id: string;
  text: string;
  quote: string | null;
  tradition: string | null;
  author: string | null;
  citation: string | null;
  analysis: string | null;
  personal_note: string | null;
  tags: string[];
  applied: boolean;
  applied_at: string | null;
  saved_at: string;
  conversation_id: string | null;
}
```

- [ ] **Step 2: Update `patchJournalEntry` to accept `personal_note`**

Update the function signature:

```typescript
export async function patchJournalEntry(
  id: string,
  body: { applied?: boolean; tags?: string[]; personal_note?: string }
): Promise<JournalEntry | null> {
  try {
    const res = await fetch(`${BASE}/api/v1/journal/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) return null;
    const json = await res.json();
    return (json.data ?? null) as JournalEntry | null;
  } catch {
    return null;
  }
}
```

- [ ] **Step 3: Commit**

```bash
git add lib/api.ts
git commit -m "feat: add personal_note to JournalEntry interface and patch fn"
```

---

## Task 5: Update the Journal UI

**Files:**
- Modify: `components/screens/JournalClient.tsx`

- [ ] **Step 1: Update `EntryRow` to accept `onSaveNote` callback**

Update the `EntryRow` props and add local state for the note:

```typescript
function EntryRow({
  entry,
  onToggleApplied,
  onDelete,
  onSaveNote,
}: {
  entry: JournalEntry;
  onToggleApplied: (id: string, current: boolean) => void;
  onDelete: (id: string) => void;
  onSaveNote: (id: string, note: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const [noteText, setNoteText] = useState(entry.personal_note ?? "");
  const [noteSaving, setNoteSaving] = useState(false);
  const hasDetail = !!(entry.quote || entry.analysis || true); // always expandable for reflection
```

Note: `hasDetail` is set to always `true` so every lesson can be expanded to add a reflection. You can keep the original condition `!!(entry.quote || entry.analysis)` if you only want already-detailed entries to be expandable — but allowing all entries to accept a reflection is the more useful behavior.

- [ ] **Step 2: Add the reflection textarea to the expanded panel**

Replace the expanded panel block (`{open && hasDetail && ...}`) with:

```typescript
      {open && (
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

          {/* Personal reflection */}
          <div className="flex flex-col gap-2 mt-1">
            <div className="font-mono text-[10px] text-muted uppercase tracking-widest">
              your reflection
            </div>
            <textarea
              className="w-full bg-paper border border-line rounded-lg px-3 py-2.5 text-[13px] leading-[1.7] resize-none outline-none focus:border-ink transition-colors text-ink placeholder:text-ink/30"
              rows={3}
              placeholder="What does this mean to you? How have you seen it show up?"
              value={noteText}
              onChange={e => setNoteText(e.target.value)}
              onBlur={async () => {
                const trimmed = noteText.trim();
                if (trimmed === (entry.personal_note ?? "").trim()) return;
                setNoteSaving(true);
                await onSaveNote(entry.id, trimmed);
                setNoteSaving(false);
              }}
            />
            {noteSaving && (
              <span className="font-mono text-[10px] text-muted">Saving…</span>
            )}
          </div>

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
```

- [ ] **Step 3: Add `handleSaveNote` to `JournalClient` and remove the global note form**

In `JournalClient`, remove all global note state (`showNoteForm`, `noteText`, `noteSaving`, `handleSaveNote`) and replace with:

```typescript
  async function handleSaveNote(id: string, note: string) {
    await patchJournalEntry(id, { personal_note: note });
    setData(d => ({
      ...d,
      entries: d.entries.map(e => e.id === id ? { ...e, personal_note: note || null } : e),
    }));
  }
```

- [ ] **Step 4: Remove the global note form from the header**

In `JournalClient`, remove the `showNoteForm` toggle button and the entire `{showNoteForm && (...)}` block. The header `<div className="flex gap-2">` can be removed entirely if empty.

- [ ] **Step 5: Pass `onSaveNote` to each `EntryRow`**

In the `filtered.map(...)` block:

```typescript
                {filtered.map((entry, i) => (
                  <div key={entry.id} className={i ? "border-t border-line-soft" : ""}>
                    <EntryRow
                      entry={entry}
                      onToggleApplied={handleToggleApplied}
                      onDelete={handleDelete}
                      onSaveNote={handleSaveNote}
                    />
                  </div>
                ))}
```

- [ ] **Step 6: Verify TypeScript compiles**

```bash
cd /Volumes/External/soulra
npx tsc --noEmit
```

Expected: No errors.

- [ ] **Step 7: Commit**

```bash
git add components/screens/JournalClient.tsx
git commit -m "feat: add per-lesson personal reflection, remove global note form"
```

---

## Task 6: Manual smoke test

- [ ] Start backend: `cd soulra-backend && uvicorn soulra.main:app --reload --port 8000`
- [ ] Start frontend: `cd /Volumes/External/soulra && npm run dev`
- [ ] Open `http://localhost:3000/journal`
- [ ] Confirm the "+ Add a private note" button is gone from the header
- [ ] Click `›` on any lesson entry — it should expand
- [ ] Type a reflection in the "your reflection" textarea, then click outside (blur)
- [ ] The "Saving…" indicator should appear briefly then disappear
- [ ] Refresh the page — the reflection should persist
- [ ] Confirm existing `applied`/`Mark applied` toggle still works
