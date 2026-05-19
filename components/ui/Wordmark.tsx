// components/ui/Wordmark.tsx
import { cn } from "@/lib/utils";

interface WordmarkProps {
  size?: number;
  className?: string;
}

export function Wordmark({ size = 22, className }: WordmarkProps) {
  return (
    <span
      className={cn("font-serif font-medium uppercase", className)}
      style={{ fontSize: size, letterSpacing: size * 0.15 }}
    >
      Soulra
    </span>
  );
}
