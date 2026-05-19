// components/conversation/CitationBadge.tsx
interface CitationBadgeProps {
  tradition: string;
  book: string;
  chapter: string;
}

export function CitationBadge({ tradition, book, chapter }: CitationBadgeProps) {
  return (
    <div className="flex items-center gap-2 font-mono text-[10px] text-accent pt-2.5 border-t border-dashed border-line mt-3.5">
      <span>↳</span>
      <span>{tradition} · {book} · {chapter}</span>
      <span className="ml-auto text-muted cursor-pointer">tap to read original ↗</span>
    </div>
  );
}
