// components/layout/Sidebar.tsx
"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Wordmark } from "@/components/ui";
import { listConversations, formatRelativeDate } from "@/lib/api";
import type { Conversation } from "@/lib/api";

const NAV_ITEMS = [
  { href: "/home",          label: "Today",            glyph: "·" },
  { href: "/chat",          label: "New conversation", glyph: "+" },
  { href: "/journal",       label: "Journal",          glyph: "◇" },
  { href: "/traditions",    label: "Traditions",       glyph: "◯" },
  { href: "/daily",         label: "Daily practice",   glyph: "✓" },
];

export function Sidebar() {
  const pathname = usePathname();
  const [conversations, setConversations] = useState<Conversation[]>([]);

  useEffect(() => {
    listConversations(8).then(setConversations).catch(() => {});
  }, [pathname]);

  return (
    <aside className="w-[220px] border-r border-line bg-paper-alt flex flex-col flex-shrink-0">
      <div className="px-4 py-5 pb-[18px]">
        <Link href="/">
          <Wordmark size={18} />
        </Link>
      </div>
      <nav className="flex flex-col gap-1 px-4">
        {NAV_ITEMS.map(item => {
          const active = pathname === item.href || (item.href === "/chat" && pathname === "/chat" && !pathname.includes("?"));
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

      {conversations.length > 0 && (
        <div className="mt-4 px-4">
          <div className="font-mono text-[9px] text-muted uppercase tracking-widest mb-1.5 px-2.5">
            Recent
          </div>
          <div className="flex flex-col gap-0.5">
            {conversations.map(conv => {
              const href = `/chat?id=${conv.id}`;
              const active = pathname.startsWith("/chat") && pathname.includes(conv.id);
              return (
                <Link
                  key={conv.id}
                  href={href}
                  className={[
                    "flex flex-col px-2.5 py-2 rounded-md transition-colors",
                    active ? "bg-paper border border-line" : "border border-transparent hover:bg-paper/50",
                  ].join(" ")}
                >
                  <span className="text-[12px] text-ink leading-tight truncate">
                    {conv.situation.slice(0, 36)}{conv.situation.length > 36 ? "…" : ""}
                  </span>
                  <span className="font-mono text-[9px] text-muted mt-0.5">
                    {formatRelativeDate(conv.created_at)}
                  </span>
                </Link>
              );
            })}
          </div>
        </div>
      )}

      <div className="mt-auto px-4 py-3 border-t border-line">
        <p className="font-mono text-[10px] text-muted leading-relaxed">
          Free · 3 of 5<br />queries this week
        </p>
      </div>
    </aside>
  );
}
