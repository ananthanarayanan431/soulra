"use client";
import { useRef, useState } from "react";
import { Button } from "@/components/ui";
import { ingestPdf, ingestUrl, ingestText, ingestYoutube, getIngestJob } from "@/lib/api";
import type { IngestJob } from "@/lib/api";

type Mode = "pdf" | "url" | "youtube" | "text";

type JobState =
  | { phase: "idle" }
  | { phase: "submitting" }
  | { phase: "processing"; jobId: string }
  | { phase: "done"; chunks: number }
  | { phase: "error"; message: string };

interface Props {
  traditionSlug: string;
  traditionName: string;
  traditionEra: string;
  onDone?: () => void;
  onCancel: () => void;
}

function ModeTab({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`font-mono text-[10px] uppercase tracking-widest px-3 py-1.5 rounded-md border transition-colors ${
        active
          ? "border-ink bg-ink text-paper"
          : "border-line text-muted hover:border-ink hover:text-ink"
      }`}
    >
      {label}
    </button>
  );
}

export function IngestPanel({ traditionSlug, traditionName, traditionEra, onDone, onCancel }: Props) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [mode, setMode] = useState<Mode>("pdf");
  const [author, setAuthor] = useState("");
  const [source, setSource] = useState("");
  const [url, setUrl] = useState("");
  const [text, setText] = useState("");
  const [fileName, setFileName] = useState("");
  const [jobState, setJobState] = useState<JobState>({ phase: "idle" });

  const busy = jobState.phase === "submitting" || jobState.phase === "processing";

  function switchMode(m: Mode) {
    setMode(m);
    setUrl("");
    setText("");
    setFileName("");
    setJobState({ phase: "idle" });
  }

  function pollJob(jobId: string) {
    const interval = setInterval(async () => {
      const job = await getIngestJob(jobId);
      if (!job) return;
      if (job.status === "done") {
        clearInterval(interval);
        setJobState({ phase: "done", chunks: job.chunks_created ?? 0 });
        onDone?.();
      } else if (job.status === "failed") {
        clearInterval(interval);
        setJobState({ phase: "error", message: job.error ?? "Ingestion failed" });
      }
    }, 2000);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setJobState({ phase: "submitting" });

    try {
      const fd = new FormData();
      fd.append("tradition", traditionSlug);
      fd.append("author", author.trim());
      fd.append("source", source.trim());
      fd.append("era", traditionEra);

      let result: IngestJob | null = null;

      if (mode === "pdf") {
        const file = fileRef.current?.files?.[0];
        if (!file) { setJobState({ phase: "error", message: "No file selected" }); return; }
        fd.append("file", file);
        result = await ingestPdf(fd);
      } else if (mode === "url") {
        fd.append("url", url.trim());
        result = await ingestUrl(fd);
      } else if (mode === "youtube") {
        fd.append("url", url.trim());
        result = await ingestYoutube(fd);
      } else {
        fd.append("content", text.trim());
        result = await ingestText(fd);
      }

      if (!result) throw new Error("No response from server");
      setJobState({ phase: "processing", jobId: result.job_id });
      pollJob(result.job_id);
    } catch (err) {
      setJobState({ phase: "error", message: err instanceof Error ? err.message : "Submission failed" });
    }
  }

  const canSubmit =
    !busy &&
    author.trim() &&
    source.trim() &&
    ((mode === "pdf" && !!fileName) ||
      (mode === "url" && !!url.trim()) ||
      (mode === "youtube" && !!url.trim()) ||
      (mode === "text" && !!text.trim()));

  return (
    <form
      onSubmit={handleSubmit}
      className="border-[1.5px] border-dashed border-ink rounded-xl p-5 bg-paper-alt flex flex-col gap-4"
    >
      <div className="flex items-center justify-between">
        <div className="font-mono text-[10px] text-accent uppercase tracking-widest">
          add content · {traditionName}
        </div>
        <button
          type="button"
          onClick={onCancel}
          className="font-mono text-[10px] text-muted hover:text-ink transition-colors"
        >
          cancel ✕
        </button>
      </div>

      {/* mode tabs */}
      <div className="flex gap-2 flex-wrap">
        <ModeTab label="PDF" active={mode === "pdf"} onClick={() => switchMode("pdf")} />
        <ModeTab label="URL" active={mode === "url"} onClick={() => switchMode("url")} />
        <ModeTab label="YouTube" active={mode === "youtube"} onClick={() => switchMode("youtube")} />
        <ModeTab label="Text" active={mode === "text"} onClick={() => switchMode("text")} />
      </div>

      {/* author + source */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="font-mono text-[9px] text-muted uppercase tracking-widest block mb-1">
            Author *
          </label>
          <input
            required
            value={author}
            onChange={e => setAuthor(e.target.value)}
            placeholder="e.g. Marcus Aurelius"
            className="w-full border border-line rounded-lg px-3 py-2 text-[13px] bg-paper focus:outline-none focus:border-ink"
          />
        </div>
        <div>
          <label className="font-mono text-[9px] text-muted uppercase tracking-widest block mb-1">
            Source title *
          </label>
          <input
            required
            value={source}
            onChange={e => setSource(e.target.value)}
            placeholder="e.g. Meditations"
            className="w-full border border-line rounded-lg px-3 py-2 text-[13px] bg-paper focus:outline-none focus:border-ink"
          />
        </div>
      </div>

      {/* mode-specific input */}
      {mode === "pdf" && (
        <div>
          <label className="font-mono text-[9px] text-muted uppercase tracking-widest block mb-1">
            PDF file *
          </label>
          <div
            className="border border-dashed border-line rounded-xl p-5 flex flex-col items-center gap-2 cursor-pointer hover:border-ink transition-colors"
            onClick={() => fileRef.current?.click()}
          >
            <span className="font-mono text-[24px] text-muted">↑</span>
            <span className="text-[13px] text-ink">{fileName || "Click to choose a PDF"}</span>
            <input
              ref={fileRef}
              type="file"
              accept="application/pdf"
              className="hidden"
              onChange={e => {
                setFileName(e.target.files?.[0]?.name ?? "");
                setJobState({ phase: "idle" });
              }}
            />
          </div>
        </div>
      )}

      {mode === "url" && (
        <div>
          <label className="font-mono text-[9px] text-muted uppercase tracking-widest block mb-1">
            URL *
          </label>
          <input
            required
            type="url"
            value={url}
            onChange={e => setUrl(e.target.value)}
            placeholder="https://example.com/text"
            className="w-full border border-line rounded-lg px-3 py-2 text-[13px] bg-paper focus:outline-none focus:border-ink"
          />
        </div>
      )}

      {mode === "youtube" && (
        <div>
          <label className="font-mono text-[9px] text-muted uppercase tracking-widest block mb-1">
            YouTube URL *
          </label>
          <input
            required
            type="url"
            value={url}
            onChange={e => setUrl(e.target.value)}
            placeholder="https://youtube.com/watch?v=..."
            className="w-full border border-line rounded-lg px-3 py-2 text-[13px] bg-paper focus:outline-none focus:border-ink"
          />
          <div className="font-mono text-[9px] text-muted mt-1.5">
            Extracts the video transcript — captions must be available on the video
          </div>
        </div>
      )}

      {mode === "text" && (
        <div>
          <label className="font-mono text-[9px] text-muted uppercase tracking-widest block mb-1">
            Text *
          </label>
          <textarea
            required
            value={text}
            onChange={e => setText(e.target.value)}
            rows={5}
            placeholder="Paste the text you want to index…"
            className="w-full border border-line rounded-lg px-3 py-2 text-[13px] bg-paper focus:outline-none focus:border-ink resize-none"
          />
        </div>
      )}

      {/* status */}
      {jobState.phase === "processing" && (
        <div className="font-mono text-[11px] text-accent animate-pulse">
          Processing — chunking &amp; embedding…
        </div>
      )}
      {jobState.phase === "done" && (
        <div className="font-mono text-[11px] text-green-700">
          Done — {jobState.chunks} chunks indexed ✓
        </div>
      )}
      {jobState.phase === "error" && (
        <div className="font-mono text-[11px] text-red-700">{jobState.message}</div>
      )}

      {/* actions */}
      <div className="flex gap-2 items-center">
        <Button small primary type="submit" disabled={!canSubmit}>
          {jobState.phase === "submitting"
            ? "Submitting…"
            : jobState.phase === "processing"
              ? "Processing…"
              : "Upload & index"}
        </Button>
        {jobState.phase === "done" && (
          <button
            type="button"
            onClick={onCancel}
            className="font-mono text-[10px] text-muted hover:text-ink transition-colors"
          >
            Close
          </button>
        )}
      </div>
    </form>
  );
}
