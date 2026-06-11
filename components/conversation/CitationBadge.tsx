interface CitationBadgeProps {
  tradition: string;
  book: string;
  chapter: string;
  onReadOriginal?: () => void;
  showingOriginal?: boolean;
  hasPassage?: boolean;
}

export function CitationBadge({ tradition, book, chapter, onReadOriginal, showingOriginal, hasPassage }: CitationBadgeProps) {
  return (
    <div className="flex items-center gap-2 font-mono text-[10px] text-accent pt-2.5 border-t border-dashed border-line mt-3.5">
      <span>↳</span>
      <span>{tradition} · {book} · {chapter}</span>
      {hasPassage && (
        <button
          type="button"
          onClick={onReadOriginal}
          className="ml-auto text-muted hover:text-ink transition-colors"
        >
          {showingOriginal ? "hide original ↑" : "read original ↗"}
        </button>
      )}
    </div>
  );
}
