"use client";
import { useState, useTransition, type FormEvent, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { Sidebar } from "@/components/layout";
import { Chip } from "@/components/ui";
import { IngestPanel } from "@/components/traditions/IngestPanel";
import type { Tradition, TraditionInput, TraditionsData } from "@/lib/api";
import {
  updateTraditionPreferences,
  createTradition,
  updateTradition,
  deleteTradition,
} from "@/lib/api";

const EMPTY_FORM = { name: "", origin: "", era: "", description: "" };

function slugify(name: string): string {
  return name
    .toLowerCase()
    .trim()
    .replace(/[^\w\s-]/g, "")
    .replace(/[\s_]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <label className="font-mono text-[9px] text-muted uppercase tracking-widest block mb-1">{label}</label>
      {children}
    </div>
  );
}

export function TraditionsClient({ initialData }: { initialData: TraditionsData }) {
  const router = useRouter();
  const [traditions, setTraditions] = useState<Tradition[]>(initialData.traditions);
  const [selectedEra, setSelectedEra] = useState<string>("all");
  const [selectedSlugs, setSelectedSlugs] = useState<Set<string>>(
    () => new Set(initialData.traditions.filter(t => t.selected).map(t => t.slug))
  );
  const [, startTransition] = useTransition();

  const [showCreate, setShowCreate] = useState(false);
  const [createForm, setCreateForm] = useState(EMPTY_FORM);
  const [createBusy, setCreateBusy] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  const [editingSlug, setEditingSlug] = useState<string | null>(null);
  const [editForm, setEditForm] = useState(EMPTY_FORM);
  const [editBusy, setEditBusy] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);

  const [confirmingSlug, setConfirmingSlug] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<{ slug: string; message: string } | null>(null);
  const [infoSlug, setInfoSlug] = useState<string | null>(null);
  const [ingestSlug, setIngestSlug] = useState<string | null>(null);

  const eras = ["all", ...Array.from(new Set(traditions.map(t => t.era))).sort()];
  const visible = selectedEra === "all" ? traditions : traditions.filter(t => t.era === selectedEra);
  const selectedTraditions = traditions.filter(t => selectedSlugs.has(t.slug));
  const totalSources = traditions.reduce((sum, t) => sum + t.sources, 0);
  const totalPassages = traditions.reduce((sum, t) => sum + t.passages, 0);

  function closeOverlays() {
    setShowCreate(false);
    setEditingSlug(null);
    setConfirmingSlug(null);
    setInfoSlug(null);
    setIngestSlug(null);
  }

  function toggleTradition(slug: string) {
    const next = new Set(selectedSlugs);
    next.has(slug) ? next.delete(slug) : next.add(slug);
    const slugs = Array.from(next);
    setSelectedSlugs(next);
    startTransition(() => { updateTraditionPreferences(slugs); });
  }

  function toggleCreateForm() {
    if (showCreate) {
      setShowCreate(false);
      return;
    }
    closeOverlays();
    setCreateForm(EMPTY_FORM);
    setCreateError(null);
    setShowCreate(true);
  }

  async function handleCreateSubmit(e: FormEvent) {
    e.preventDefault();
    const name = createForm.name.trim();
    const origin = createForm.origin.trim();
    const era = createForm.era.trim();
    if (!name || !origin || !era) return;

    setCreateBusy(true);
    setCreateError(null);
    try {
      const input: TraditionInput = { name, origin, era };
      if (createForm.description.trim()) input.description = createForm.description.trim();
      const created = await createTradition(input);
      setTraditions(prev => [...prev, created]);
      setShowCreate(false);
      setCreateForm(EMPTY_FORM);
      setIngestSlug(created.slug);
    } catch (err) {
      setCreateError(err instanceof Error ? err.message : "Failed to create tradition");
    } finally {
      setCreateBusy(false);
    }
  }

  function startEditing(t: Tradition) {
    closeOverlays();
    setEditingSlug(t.slug);
    setEditForm({ name: t.name, origin: t.origin, era: t.era, description: t.description ?? "" });
    setEditError(null);
  }

  async function handleEditSubmit(e: FormEvent, slug: string) {
    e.preventDefault();
    const name = editForm.name.trim();
    const origin = editForm.origin.trim();
    const era = editForm.era.trim();
    if (!name || !origin || !era) return;

    setEditBusy(true);
    setEditError(null);
    try {
      const input: Partial<TraditionInput> = {
        name,
        origin,
        era,
        description: editForm.description.trim(),
      };
      const updated = await updateTradition(slug, input);
      setTraditions(prev => prev.map(t => (t.slug === slug ? updated : t)));
      setEditingSlug(null);
    } catch (err) {
      setEditError(err instanceof Error ? err.message : "Failed to update tradition");
    } finally {
      setEditBusy(false);
    }
  }

  function handleDeleteClick(slug: string) {
    if (confirmingSlug !== slug) {
      setConfirmingSlug(slug);
      window.setTimeout(() => {
        setConfirmingSlug(prev => (prev === slug ? null : prev));
      }, 3000);
      return;
    }
    setConfirmingSlug(null);
    setDeleteError(null);
    void performDelete(slug);
  }

  async function performDelete(slug: string) {
    try {
      await deleteTradition(slug);
    } catch (err) {
      setDeleteError({ slug, message: err instanceof Error ? err.message : "Failed to delete tradition" });
      return;
    }
    setTraditions(prev => prev.filter(t => t.slug !== slug));
    setInfoSlug(prev => (prev === slug ? null : prev));
    setEditingSlug(prev => (prev === slug ? null : prev));
    if (selectedSlugs.has(slug)) {
      const next = new Set(selectedSlugs);
      next.delete(slug);
      const slugs = Array.from(next);
      setSelectedSlugs(next);
      startTransition(() => { updateTraditionPreferences(slugs); });
    }
  }

  function toggleInfo(slug: string) {
    if (infoSlug === slug) {
      setInfoSlug(null);
      return;
    }
    closeOverlays();
    setInfoSlug(slug);
  }

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
                  <span key={t.slug} className="text-[11px] px-2.5 py-1 rounded-full bg-ink text-paper">
                    {t.name} ×
                  </span>
                ))}
              </div>
            </div>
            <div className="font-mono text-[10px] text-muted leading-relaxed text-right flex-shrink-0">
              {totalSources.toLocaleString()} source texts<br />
              {totalPassages.toLocaleString()} passages indexed
            </div>
          </div>

          {/* era filters + add control */}
          <div className="flex items-center gap-2 mb-6">
            <span className="font-mono text-[10px] text-muted self-center mr-1">filter:</span>
            {eras.map(era => (
              <Chip key={era} active={era === selectedEra} onClick={() => setSelectedEra(era)}>
                {era}
              </Chip>
            ))}
            <button
              type="button"
              onClick={toggleCreateForm}
              className="ml-auto font-mono text-[10px] uppercase tracking-widest text-muted hover:text-ink transition-colors underline underline-offset-4"
            >
              {showCreate ? "cancel" : "+ add tradition"}
            </button>
          </div>

          {/* create form */}
          {showCreate && (
            <form onSubmit={handleCreateSubmit} className="border-[1.5px] border-dashed border-ink rounded-xl p-5 mb-6 bg-paper-alt">
              <div className="font-mono text-[10px] text-muted uppercase tracking-widest mb-4">new tradition</div>
              <div className="grid grid-cols-3 gap-3 mb-3">
                <Field label="Name *">
                  <input
                    required
                    value={createForm.name}
                    onChange={e => setCreateForm(f => ({ ...f, name: e.target.value }))}
                    placeholder="e.g. Hermeticism"
                    className="w-full border border-line rounded-lg px-3 py-2 text-[13px] bg-paper focus:outline-none focus:border-ink"
                  />
                </Field>
                <Field label="Origin *">
                  <input
                    required
                    value={createForm.origin}
                    onChange={e => setCreateForm(f => ({ ...f, origin: e.target.value }))}
                    placeholder="e.g. Egypt · ~200 CE"
                    className="w-full border border-line rounded-lg px-3 py-2 text-[13px] bg-paper focus:outline-none focus:border-ink"
                  />
                </Field>
                <Field label="Era *">
                  <input
                    required
                    list="tradition-era-options"
                    value={createForm.era}
                    onChange={e => setCreateForm(f => ({ ...f, era: e.target.value }))}
                    placeholder="ancient, medieval…"
                    className="w-full border border-line rounded-lg px-3 py-2 text-[13px] bg-paper focus:outline-none focus:border-ink"
                  />
                </Field>
              </div>
              <Field label="Description (optional)">
                <input
                  value={createForm.description}
                  onChange={e => setCreateForm(f => ({ ...f, description: e.target.value }))}
                  placeholder="Shown in the (i) info popover on the card"
                  className="w-full border border-line rounded-lg px-3 py-2 text-[13px] bg-paper focus:outline-none focus:border-ink"
                />
              </Field>
              <div className="flex items-center gap-3 mt-4">
                <button
                  type="submit"
                  disabled={createBusy}
                  className="font-mono text-[10px] uppercase tracking-widest px-4 py-2 rounded-lg bg-ink text-paper disabled:opacity-50"
                >
                  {createBusy ? "creating…" : "create tradition →"}
                </button>
                <span className="font-mono text-[10px] text-muted">
                  {createForm.name.trim()
                    ? `slug: ${slugify(createForm.name.trim())} · `
                    : ""}
                  then upload PDF, URL, YouTube, or text
                </span>
              </div>
              {createError && <div className="font-mono text-[10px] text-red-600 mt-3">{createError}</div>}
            </form>
          )}

          <datalist id="tradition-era-options">
            {eras.filter(e => e !== "all").map(e => <option key={e} value={e} />)}
          </datalist>

          {/* ingest panel — shown when a tradition is selected for content upload */}
          {ingestSlug && (() => {
            const t = traditions.find(x => x.slug === ingestSlug);
            if (!t) return null;
            return (
              <div className="mb-6">
                <IngestPanel
                  traditionSlug={t.slug}
                  traditionName={t.name}
                  traditionEra={t.era}
                  onDone={() => router.refresh()}
                  onCancel={() => setIngestSlug(null)}
                />
              </div>
            );
          })()}

          {/* tradition cards grid */}
          {visible.length === 0 ? (
            <div className="border border-dashed border-line rounded-xl p-10 text-center font-mono text-[11px] text-muted">
              {traditions.length === 0 ? "No traditions yet — add your first one above." : "No traditions in this era."}
            </div>
          ) : (
            <div className="grid grid-cols-3 gap-3">
              {visible.map(t => {
                const isPicked = selectedSlugs.has(t.slug);

                if (editingSlug === t.slug) {
                  return (
                    <form
                      key={t.slug}
                      onSubmit={e => handleEditSubmit(e, t.slug)}
                      className="rounded-xl p-5 border-[1.5px] border-ink bg-paper"
                    >
                      <div className="font-mono text-[9px] text-muted uppercase tracking-widest mb-3">editing · {t.slug}</div>
                      <div className="space-y-2 mb-3">
                        <input
                          required
                          value={editForm.name}
                          onChange={e => setEditForm(f => ({ ...f, name: e.target.value }))}
                          placeholder="Name"
                          className="w-full border border-line rounded-lg px-2.5 py-1.5 text-[12px] bg-paper focus:outline-none focus:border-ink"
                        />
                        <input
                          required
                          value={editForm.origin}
                          onChange={e => setEditForm(f => ({ ...f, origin: e.target.value }))}
                          placeholder="Origin"
                          className="w-full border border-line rounded-lg px-2.5 py-1.5 text-[12px] bg-paper focus:outline-none focus:border-ink"
                        />
                        <input
                          required
                          list="tradition-era-options"
                          value={editForm.era}
                          onChange={e => setEditForm(f => ({ ...f, era: e.target.value }))}
                          placeholder="Era"
                          className="w-full border border-line rounded-lg px-2.5 py-1.5 text-[12px] bg-paper focus:outline-none focus:border-ink"
                        />
                        <input
                          value={editForm.description}
                          onChange={e => setEditForm(f => ({ ...f, description: e.target.value }))}
                          placeholder="Description (optional)"
                          className="w-full border border-line rounded-lg px-2.5 py-1.5 text-[12px] bg-paper focus:outline-none focus:border-ink"
                        />
                      </div>
                      {editError && <div className="font-mono text-[9px] text-red-600 mb-2">{editError}</div>}
                      <div className="flex gap-2">
                        <button
                          type="submit"
                          disabled={editBusy}
                          className="font-mono text-[9px] uppercase tracking-widest px-3 py-1.5 rounded-lg bg-ink text-paper disabled:opacity-50"
                        >
                          {editBusy ? "saving…" : "save"}
                        </button>
                        <button
                          type="button"
                          onClick={() => setEditingSlug(null)}
                          className="font-mono text-[9px] uppercase tracking-widest px-3 py-1.5 rounded-lg border border-line text-muted"
                        >
                          cancel
                        </button>
                      </div>
                    </form>
                  );
                }

                return (
                  <div key={t.slug} className="relative group">
                    <div
                      role="button"
                      tabIndex={0}
                      onClick={() => toggleTradition(t.slug)}
                      onKeyDown={e => {
                        if (e.key === "Enter" || e.key === " ") {
                          e.preventDefault();
                          toggleTradition(t.slug);
                        }
                      }}
                      className={`cursor-pointer rounded-xl p-5 transition-all ${
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
                        <div className="flex items-center gap-1.5 flex-shrink-0">
                          <button
                            type="button"
                            onClick={e => { e.stopPropagation(); toggleInfo(t.slug); }}
                            title="About this tradition"
                            className={`w-[15px] h-[15px] rounded-full border font-serif italic text-[9px] flex items-center justify-center leading-none ${
                              isPicked ? "border-accent-soft text-accent-soft" : "border-line text-muted hover:border-ink hover:text-ink"
                            }`}
                          >
                            i
                          </button>
                          <span className={`font-mono text-[13px] mt-0.5 ${isPicked ? "text-accent-soft" : "text-muted"}`}>
                            {isPicked ? "✓" : "+"}
                          </span>
                        </div>
                      </div>
                      <div className={`font-mono text-[10px] mt-3 pt-3 border-t ${isPicked ? "border-[#3a352d] text-accent-soft" : "border-dashed border-line text-muted"}`}>
                        {t.sources} sources &middot; {t.passages.toLocaleString()} passages
                      </div>
                    </div>

                    {infoSlug === t.slug && (
                      <div className="absolute top-12 right-4 w-[230px] rounded-lg bg-ink text-paper p-3 text-[10px] leading-relaxed shadow-lg z-10">
                        <div className="font-mono text-[8px] uppercase tracking-widest text-accent-soft mb-1.5">
                          about {t.name.toLowerCase()}
                        </div>
                        {t.description?.trim() ? t.description : "No description yet."}
                        <div className="mt-2 font-mono text-[9px] text-accent-soft">
                          slug: {t.slug} &middot; era: {t.era}
                        </div>
                      </div>
                    )}

                    <div className="absolute bottom-3 right-4 flex items-center gap-2.5 opacity-0 group-hover:opacity-100 transition-opacity">
                      {deleteError?.slug === t.slug && (
                        <span className="font-mono text-[9px] text-red-600">{deleteError.message}</span>
                      )}
                      <button
                        type="button"
                        onClick={e => { e.stopPropagation(); closeOverlays(); setIngestSlug(t.slug); }}
                        className={`font-mono text-[9px] uppercase tracking-widest ${isPicked ? "text-accent-soft hover:text-paper" : "text-muted hover:text-ink"}`}
                      >
                        upload
                      </button>
                      <button
                        type="button"
                        onClick={e => { e.stopPropagation(); startEditing(t); }}
                        className={`font-mono text-[9px] uppercase tracking-widest ${isPicked ? "text-accent-soft hover:text-paper" : "text-muted hover:text-ink"}`}
                      >
                        edit
                      </button>
                      <button
                        type="button"
                        onClick={e => { e.stopPropagation(); handleDeleteClick(t.slug); }}
                        className={`font-mono text-[9px] uppercase tracking-widest ${
                          confirmingSlug === t.slug ? "text-red-600" : isPicked ? "text-accent-soft hover:text-paper" : "text-muted hover:text-ink"
                        }`}
                      >
                        {confirmingSlug === t.slug ? "confirm?" : "remove"}
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
