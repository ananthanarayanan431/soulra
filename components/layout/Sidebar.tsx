// components/layout/Sidebar.tsx
"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Wordmark } from "@/components/ui";

const NAV_ITEMS = [
  { href: "/home",        label: "Today",            glyph: "·" },
  { href: "/chat",        label: "New conversation", glyph: "+" },
  { href: "/journal",     label: "Journal",          glyph: "◇" },
  { href: "/traditions",  label: "Traditions",       glyph: "◯" },
  { href: "/daily",       label: "Daily practice",   glyph: "✓" },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-[220px] border-r border-line bg-paper-alt flex flex-col flex-shrink-0">
      <div className="px-4 py-5 pb-[18px]">
        <Wordmark size={18} />
      </div>
      <nav className="flex flex-col gap-1 px-4">
        {NAV_ITEMS.map(item => {
          const active = pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={[
                "flex items-center gap-2.5 px-2.5 py-2 rounded-md text-sm text-ink transition-colors",
                active ? "bg-paper border border-line" : "border border-transparent hover:bg-paper/50",
              ].join(" ")}
            >
              <span className="font-mono text-muted w-3 text-[11px]">{item.glyph}</span>
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>
      <div className="mt-auto px-4 py-3 border-t border-line">
        <p className="font-mono text-[10px] text-muted leading-relaxed">
          Free · 3 of 5<br />queries this week
        </p>
      </div>
    </aside>
  );
}
