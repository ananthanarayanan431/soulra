// components/ui/Chip.tsx
import { cn } from "@/lib/utils";

interface ChipProps {
  children: React.ReactNode;
  active?: boolean;
  className?: string;
  onClick?: () => void;
}

export function Chip({ children, active, className, onClick }: ChipProps) {
  const Tag = onClick ? "button" : "span";
  return (
    <Tag
      type={onClick ? "button" : undefined}
      onClick={onClick}
      className={cn(
        "inline-flex items-center px-3 py-1 rounded-full text-xs font-sans border transition-colors",
        active ? "border-ink bg-ink text-paper" : "border-line bg-transparent text-ink",
        onClick && "cursor-pointer hover:border-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink",
        className,
      )}
    >
      {children}
    </Tag>
  );
}
