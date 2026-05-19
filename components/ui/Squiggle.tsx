import { cn } from "@/lib/utils";

interface SquiggleProps {
  width?: number;
  color?: string;
  className?: string;
}

export function Squiggle({ width = 80, color = "currentColor", className }: SquiggleProps) {
  const w = width;
  return (
    <svg
      width={w}
      height={6}
      viewBox={`0 0 ${w} 6`}
      aria-hidden="true"
      className={cn("text-ink", className)}
    >
      <path
        d={`M 0 3 Q ${w * 0.15} 0, ${w * 0.3} 3 T ${w * 0.6} 3 T ${w * 0.9} 3 T ${w} 3`}
        fill="none"
        stroke={color}
        strokeWidth={1.2}
        strokeLinecap="round"
      />
    </svg>
  );
}
