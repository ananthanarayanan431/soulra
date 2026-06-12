// components/ui/Logo.tsx
import { cn } from "@/lib/utils";
import { LogoMark } from "./LogoMark";
import { Wordmark } from "./Wordmark";

interface LogoProps {
  size?: number;
  className?: string;
}

export function Logo({ size = 22, className }: LogoProps) {
  return (
    <span className={cn("inline-flex items-center gap-2", className)}>
      <LogoMark size={size * 1.1} />
      <Wordmark size={size} />
    </span>
  );
}
