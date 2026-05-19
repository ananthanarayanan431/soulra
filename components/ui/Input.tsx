"use client";
import { cn } from "@/lib/utils";

interface InputProps {
  placeholder?: string;
  value?: string;
  big?: boolean;
  onChange?: (value: string) => void;
  onSubmit?: () => void;
  className?: string;
}

export function Input({
  placeholder = "Tell Soulra what's on your mind…",
  value,
  big,
  onChange,
  onSubmit,
  className,
}: InputProps) {
  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      onSubmit?.();
    }
  }

  return (
    <div
      className={cn(
        "border border-ink rounded-xl bg-paper flex items-end gap-2.5 font-sans",
        big ? "p-4 min-h-[88px]" : "p-3 min-h-[44px]",
        className,
      )}
    >
      <textarea
        value={value ?? ""}
        onChange={e => onChange?.(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        rows={big ? 3 : 1}
        className={cn(
          "flex-1 bg-transparent resize-none outline-none leading-relaxed placeholder:text-muted",
          big ? "text-[15px]" : "text-[13px]",
        )}
        aria-label={placeholder}
      />
      <span className="font-mono text-[10px] text-muted pb-0.5 flex-shrink-0">↵ send</span>
    </div>
  );
}
