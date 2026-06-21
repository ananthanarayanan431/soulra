// components/ui/LogoMark.tsx
import { cn } from "@/lib/utils";

interface LogoMarkProps {
  size?: number;
  className?: string;
}

const PETAL = "M16 27 C12 20 12 9 16 5 C20 9 20 20 16 27 Z";
const PETAL_ANGLES = [-56, -28, 0, 28, 56];

export function LogoMark({ size = 22, className }: LogoMarkProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      aria-hidden="true"
      className={cn("text-ink", className)}
    >
      {PETAL_ANGLES.map(angle => (
        <path
          key={angle}
          d={PETAL}
          fill="currentColor"
          opacity={angle === 0 ? 1 : 0.7}
          transform={`rotate(${angle} 16 27)`}
        />
      ))}
    </svg>
  );
}
