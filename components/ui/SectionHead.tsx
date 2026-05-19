import { cn } from "@/lib/utils";

interface SectionHeadProps {
  kicker?: string;
  title?: string;
  sub?: string;
  className?: string;
}

export function SectionHead({ kicker, title, sub, className }: SectionHeadProps) {
  return (
    <div className={cn("", className)}>
      {kicker && (
        <p className="font-mono text-[10px] text-muted uppercase tracking-widest mb-2">
          {kicker}
        </p>
      )}
      {title && (
        <h2 className="font-serif text-[28px] leading-tight font-medium">{title}</h2>
      )}
      {sub && (
        <p className="text-sm text-muted mt-2 leading-relaxed">{sub}</p>
      )}
    </div>
  );
}
