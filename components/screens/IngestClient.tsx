"use client";
import { useEffect, useRef, useState } from "react";
import { Sidebar } from "@/components/layout";
import { Button } from "@/components/ui";
import { listTraditions, listEras, createTradition, ingestPdf, getIngestJob } from "@/lib/api";
import type { Tradition, IngestJob } from "@/lib/api";

type JobState =
  | { phase: "idle" }
  | { phase: "uploading" }
  | { phase: "processing"; jobId: string }
  | { phase: "done"; job: IngestJob }
  | { phase: "error"; message: string };

function StatusBadge({ phase, job }: { phase: JobState["phase"]; job?: IngestJob }) {
  if (phase === "uploading")
    return <span className="font-mono text-[11px] text-muted">Uploading…</span>;
  if (phase === "processing")
    return (
      <span className="font-mono text-[11px] text-accent animate-pulse">
        Processing — chunking &amp; embedding…
      </span>
    );
  if (phase === "done" && job)
    return (
      <span className="font-mono text-[11px] text-green-700">
        Done — {job.chunks_created ?? 0} chunks indexed
      </span>
    );
  return null;
}

interface NewTraditionFormProps {
  eras: string[];
  onCreated: (t: Tradition) => void;
  onCancel: () => void;
}

function NewTraditionForm({ eras, onCreated, onCancel }: NewTraditionFormProps) {
  const [name, setName] = useState("");
  const [origin, setOrigin] = useState("");
  const [era, setEra] = useState(eras[0] ?? "");
  const [customEra, setCustomEra] = useState("");
  const [description, setDescription] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const isCustom = era === "__new__";
  const effectiveEra = isCustom ? customEra.trim() : era;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim() || !origin.trim() || !effectiveEra) return;
    setSaving(true);
    setError(null);
    try {
      const tradition = await createTradition({
        name: name.trim(),
        origin: origin.trim(),
        era: effectiveEra,
        description: description.trim() || undefined,
      });
      onCreated(tradition);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create tradition");
      setSaving(false);
    }
  }

  return (
    <div className="mt-2 border border-ink rounded-xl p-5 bg-paper-alt flex flex-col gap-4">
      <div className="font-mono text-[10px] text-accent uppercase tracking-widest">
        New tradition
      </div>

      <form onSubmit={handleSubmit} className="flex flex-col gap-3.5">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="font-mono text-[10px] text-muted uppercase tracking-widest block mb-1">
              Name <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={name}
              onChange={e => setName(e.target.value)}
              required
              placeholder="e.g. Bhagavad Gita"
              className="w-full border border-line rounded-lg px-3 py-2 text-[13px] bg-paper text-ink placeholder:text-muted focus:outline-none focus:border-ink"
            />
          </div>
          <div>
            <label className="font-mono text-[10px] text-muted uppercase tracking-widest block mb-1">
              Origin <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={origin}
              onChange={e => setOrigin(e.target.value)}
              required
              placeholder="e.g. India · ~200 BCE"
              className="w-full border border-line rounded-lg px-3 py-2 text-[13px] bg-paper text-ink placeholder:text-muted focus:outline-none focus:border-ink"
            />
          </div>
        </div>

        <div>
          <label className="font-mono text-[10px] text-muted uppercase tracking-widest block mb-1">
            Era <span className="text-red-500">*</span>
          </label>
          <div className="flex gap-2 flex-wrap">
            {eras.map(e => (
              <button
                key={e}
                type="button"
                onClick={() => setEra(e)}
                className={[
                  "px-3 py-1.5 rounded-md text-[13px] border transition-colors",
                  era === e
                    ? "border-ink bg-ink text-paper"
                    : "border-line text-muted hover:border-ink hover:text-ink",
                ].join(" ")}
              >
                {e}
              </button>
            ))}
            <button
              type="button"
              onClick={() => setEra("__new__")}
              className={[
                "px-3 py-1.5 rounded-md text-[13px] border transition-colors",
                era === "__new__"
                  ? "border-ink bg-ink text-paper"
                  : "border-line text-muted hover:border-ink hover:text-ink",
              ].join(" ")}
            >
              + New era
            </button>
          </div>
          {isCustom && (
            <input
              type="text"
              value={customEra}
              onChange={e => setCustomEra(e.target.value)}
              required
              placeholder="e.g. classical"
              className="mt-2 w-full border border-line rounded-lg px-3 py-2 text-[13px] bg-paper text-ink placeholder:text-muted focus:outline-none focus:border-ink"
            />
          )}
        </div>

        <div>
          <label className="font-mono text-[10px] text-muted uppercase tracking-widest block mb-1">
            Description <span className="text-muted">(optional)</span>
          </label>
          <textarea
            value={description}
            onChange={e => setDescription(e.target.value)}
            rows={2}
            placeholder="Brief description of this tradition…"
            className="w-full border border-line rounded-lg px-3 py-2 text-[13px] bg-paper text-ink placeholder:text-muted focus:outline-none focus:border-ink resize-none"
          />
        </div>

        {error && (
          <div className="font-mono text-[11px] text-red-700">{error}</div>
        )}

        <div className="flex gap-2">
          <Button primary small disabled={saving || !name.trim() || !origin.trim() || !effectiveEra}>
            {saving ? "Creating…" : "Create tradition"}
          </Button>
          <Button small onClick={onCancel}>Cancel</Button>
        </div>
      </form>
    </div>
  );
}

export function IngestClient() {
  const fileRef = useRef<HTMLInputElement>(null);
  const [traditions, setTraditions] = useState<Tradition[]>([]);
  const [eras, setEras] = useState<string[]>([]);
  const [loadingData, setLoadingData] = useState(true);

  const [tradition, setTradition] = useState("");
  const [author, setAuthor] = useState("");
  const [source, setSource] = useState("");
  const [era, setEra] = useState("");
  const [jobState, setJobState] = useState<JobState>({ phase: "idle" });
  const [jobs, setJobs] = useState<IngestJob[]>([]);
  const [showNewTradition, setShowNewTradition] = useState(false);

  useEffect(() => {
    Promise.all([listTraditions(), listEras()]).then(([{ traditions: ts }, es]) => {
      setTraditions(ts);
      setEras(es);
      if (ts.length > 0) setTradition(ts[0].slug);
      if (es.length > 0) setEra(es[0]);
      setLoadingData(false);
    });
  }, []);

  function pollJob(jobId: string) {
    const interval = setInterval(async () => {
      const job = await getIngestJob(jobId);
      if (!job) return;
      if (job.status === "done") {
        clearInterval(interval);
        setJobState({ phase: "done", job });
        setJobs(prev => [job, ...prev]);
      } else if (job.status === "failed") {
        clearInterval(interval);
        setJobState({ phase: "error", message: job.error ?? "Ingestion failed" });
      }
    }, 2000);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const file = fileRef.current?.files?.[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);
    formData.append("tradition", tradition);
    formData.append("author", author);
    formData.append("source", source);
    formData.append("era", era);

    setJobState({ phase: "uploading" });
    try {
      const result = await ingestPdf(formData);
      if (!result) throw new Error("No response from server");
      setJobState({ phase: "processing", jobId: result.job_id });
      pollJob(result.job_id);
      if (fileRef.current) fileRef.current.value = "";
      setAuthor("");
      setSource("");
    } catch (err) {
      setJobState({ phase: "error", message: err instanceof Error ? err.message : "Upload failed" });
    }
  }

  function handleTraditionCreated(t: Tradition) {
    setTraditions(prev => [...prev, t].sort((a, b) => a.name.localeCompare(b.name)));
    setTradition(t.slug);
    // add new era to list if it's new
    if (!eras.includes(t.era)) {
      setEras(prev => [...prev, t.era].sort());
    }
    setEra(t.era);
    setShowNewTradition(false);
  }

  const busy = jobState.phase === "uploading" || jobState.phase === "processing";

  return (
    <div className="flex h-screen bg-paper overflow-hidden">
      <Sidebar />

      <div className="flex-1 overflow-auto px-10 py-8">
        <div className="mb-8">
          <div className="font-mono text-[10px] text-muted uppercase tracking-widest">library</div>
          <div className="font-serif text-[36px] leading-tight mt-1">Upload a text</div>
          <div className="text-[13px] text-muted mt-1.5">
            Add a PDF to the wisdom library. It will be chunked, embedded, and available to all future conversations.
          </div>
        </div>

        <div className="grid grid-cols-[1fr_320px] gap-8 max-w-[900px]">
          <form onSubmit={handleSubmit} className="flex flex-col gap-5">

            {/* tradition */}
            <div>
              <label className="font-mono text-[10px] text-muted uppercase tracking-widest block mb-1.5">
                Tradition
              </label>
              {loadingData ? (
                <div className="w-full border border-line rounded-lg px-3 py-2.5 text-[14px] text-muted bg-paper">
                  Loading…
                </div>
              ) : (
                <div className="flex gap-2 items-center">
                  <select
                    value={tradition}
                    onChange={e => setTradition(e.target.value)}
                    required
                    className="flex-1 border border-line rounded-lg px-3 py-2.5 text-[14px] bg-paper text-ink focus:outline-none focus:border-ink"
                  >
                    {traditions.map(t => (
                      <option key={t.slug} value={t.slug}>{t.name}</option>
                    ))}
                  </select>
                  <button
                    type="button"
                    onClick={() => setShowNewTradition(v => !v)}
                    className={[
                      "px-3 py-2.5 rounded-lg border text-[13px] transition-colors flex-shrink-0",
                      showNewTradition
                        ? "border-ink bg-ink text-paper"
                        : "border-line text-muted hover:border-ink hover:text-ink",
                    ].join(" ")}
                    title="Add a new tradition"
                  >
                    + New
                  </button>
                </div>
              )}

              {showNewTradition && !loadingData && (
                <NewTraditionForm
                  eras={eras}
                  onCreated={handleTraditionCreated}
                  onCancel={() => setShowNewTradition(false)}
                />
              )}
            </div>

            {/* author */}
            <div>
              <label className="font-mono text-[10px] text-muted uppercase tracking-widest block mb-1.5">
                Author
              </label>
              <input
                type="text"
                value={author}
                onChange={e => setAuthor(e.target.value)}
                required
                placeholder="e.g. Marcus Aurelius"
                className="w-full border border-line rounded-lg px-3 py-2.5 text-[14px] bg-paper text-ink placeholder:text-muted focus:outline-none focus:border-ink"
              />
            </div>

            {/* source title */}
            <div>
              <label className="font-mono text-[10px] text-muted uppercase tracking-widest block mb-1.5">
                Source title
              </label>
              <input
                type="text"
                value={source}
                onChange={e => setSource(e.target.value)}
                required
                placeholder="e.g. Meditations"
                className="w-full border border-line rounded-lg px-3 py-2.5 text-[14px] bg-paper text-ink placeholder:text-muted focus:outline-none focus:border-ink"
              />
            </div>

            {/* era */}
            <div>
              <label className="font-mono text-[10px] text-muted uppercase tracking-widest block mb-1.5">
                Era
              </label>
              {loadingData ? (
                <div className="text-[13px] text-muted">Loading…</div>
              ) : (
                <div className="flex gap-2 flex-wrap">
                  {eras.map(e => (
                    <button
                      key={e}
                      type="button"
                      onClick={() => setEra(e)}
                      className={[
                        "px-3 py-1.5 rounded-md text-[13px] border transition-colors",
                        era === e
                          ? "border-ink bg-ink text-paper"
                          : "border-line text-muted hover:border-ink hover:text-ink",
                      ].join(" ")}
                    >
                      {e}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* file picker */}
            <div>
              <label className="font-mono text-[10px] text-muted uppercase tracking-widest block mb-1.5">
                PDF file
              </label>
              <div
                className="border-[1.5px] border-dashed border-line rounded-xl p-6 flex flex-col items-center justify-center gap-2 cursor-pointer hover:border-ink transition-colors"
                onClick={() => fileRef.current?.click()}
              >
                <span className="font-mono text-[28px] text-muted">↑</span>
                <span className="text-[13px] text-ink">Click to choose a PDF</span>
                <span className="font-mono text-[10px] text-muted">
                  {fileRef.current?.files?.[0]?.name ?? "No file chosen"}
                </span>
                <input
                  ref={fileRef}
                  type="file"
                  accept="application/pdf"
                  required
                  className="hidden"
                  onChange={() => setJobState({ phase: "idle" })}
                />
              </div>
            </div>

            {/* submit */}
            <div className="flex items-center gap-4">
              <Button primary disabled={busy || loadingData}>
                {busy ? "Working…" : "Upload & index"}
              </Button>
              <StatusBadge phase={jobState.phase} job={jobState.phase === "done" ? jobState.job : undefined} />
              {jobState.phase === "error" && (
                <span className="font-mono text-[11px] text-red-700">{jobState.message}</span>
              )}
            </div>
          </form>

          {/* session log */}
          <div>
            <div className="font-mono text-[10px] text-muted uppercase tracking-widest mb-3">
              Recent uploads this session
            </div>
            {jobs.length === 0 ? (
              <div className="font-mono text-[11px] text-muted italic">None yet</div>
            ) : (
              <div className="flex flex-col gap-2">
                {jobs.map(j => (
                  <div key={j.job_id} className="border border-line rounded-lg px-3 py-2.5">
                    <div className="text-[13px] text-ink truncate">{j.filename ?? j.job_id.slice(0, 8)}</div>
                    <div className="font-mono text-[10px] text-green-700 mt-0.5">
                      ✓ {j.chunks_created ?? 0} chunks
                    </div>
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
