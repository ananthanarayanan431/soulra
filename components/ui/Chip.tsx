// components/ui/Chip.tsx
"use client";
import { cn } from "@/lib/utils";

interface ChipProps {
  children: React.ReactNode;
  active?: boolean;
  className?: string;
  onClick?: () => void;
}

export function Chip({ children, active, className, onClick }: ChipProps) {
  if (onClick) {
    return (
      <button
        type="button"
        onClick={onClick}
        className={cn(
          "inline-flex items-center px-3 py-1 rounded-full text-xs font-sans border transition-colors",
          active ? "border-ink bg-ink text-paper" : "border-line bg-transparent text-ink",
          "cursor-pointer hover:border-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink",
          className,
        )}
      >
        {children}
      </button>
    );
  }
  return (
    <span
      className={cn(
        "inline-flex items-center px-3 py-1 rounded-full text-xs font-sans border transition-colors",
        active ? "border-ink bg-ink text-paper" : "border-line bg-transparent text-ink",
        className,
      )}
    >
      {children}
    </span>
  );
}
