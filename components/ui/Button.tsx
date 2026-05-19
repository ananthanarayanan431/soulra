// components/ui/Button.tsx
import { cn } from "@/lib/utils";

interface ButtonProps {
  children: React.ReactNode;
  primary?: boolean;
  small?: boolean;
  full?: boolean;
  type?: "button" | "submit" | "reset";
  disabled?: boolean;
  onClick?: () => void;
  className?: string;
}

export function Button({
  children,
  primary,
  small,
  full,
  type = "button",
  disabled,
  onClick,
  className,
}: ButtonProps) {
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={cn(
        "inline-flex items-center justify-center rounded-full border border-ink font-sans font-medium transition-colors",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-1",
        "disabled:opacity-50 disabled:pointer-events-none",
        small ? "px-3 py-1.5 text-xs" : "px-5 py-2.5 text-sm",
        primary ? "bg-ink text-paper hover:bg-ink/90" : "bg-transparent text-ink hover:bg-ink/5",
        full && "w-full",
        className,
      )}
    >
      {children}
    </button>
  );
}
