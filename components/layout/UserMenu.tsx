// components/layout/UserMenu.tsx
"use client";
import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { useUser, useClerk } from "@clerk/nextjs";
import type { MeData } from "@/lib/api";

export function UserMenu({ me }: { me: MeData | null }) {
  const { user } = useUser();
  const { signOut } = useClerk();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function onClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, [open]);

  if (!user) return null;

  const name = user.fullName || user.primaryEmailAddress?.emailAddress || "Account";
  const email = user.primaryEmailAddress?.emailAddress ?? "";
  const initial = name.charAt(0).toUpperCase();
  const tokensLeft = me ? Math.max(0, me.token_limit - me.tokens_used) : null;
  const pct = me && me.token_limit > 0
    ? Math.min(100, (me.tokens_used / me.token_limit) * 100)
    : 0;

  return (
    <div ref={ref} className="mt-auto px-4 py-3 border-t border-line relative">
      <button
        onClick={() => setOpen(o => !o)}
        className="flex items-center gap-2.5 w-full px-2.5 py-2 rounded-md text-sm text-ink border border-transparent hover:bg-paper/50 transition-colors"
      >
        {user.imageUrl ? (
          <Image
            src={user.imageUrl}
            alt=""
            width={28}
            height={28}
            unoptimized
            className="w-7 h-7 rounded-full flex-shrink-0"
          />
        ) : (
          <span className="w-7 h-7 rounded-full bg-ink text-paper flex items-center justify-center text-[12px] font-medium flex-shrink-0">
            {initial}
          </span>
        )}
        <span className="truncate flex-1 text-left">{name}</span>
        <span className="font-mono text-muted text-[11px]">▾</span>
      </button>

      {open && (
        <div className="absolute left-4 right-4 bottom-full mb-2 bg-paper border border-line rounded-xl shadow-sm p-3 z-10">
          <div className="text-sm font-medium truncate">{name}</div>
          {email && (
            <div className="font-mono text-[10px] text-muted truncate mt-0.5">{email}</div>
          )}

          {me && (
            <>
              <div className="border-t border-line-soft my-2" />
              <div className="font-mono text-[9px] text-muted uppercase tracking-widest mb-1.5">
                Token usage
              </div>
              <div className="h-1.5 rounded-full bg-paper-alt overflow-hidden">
                <div className="h-full bg-accent" style={{ width: `${pct}%` }} />
              </div>
              <div className="font-mono text-[10px] text-muted mt-1.5">
                {tokensLeft!.toLocaleString()} tokens left
              </div>
            </>
          )}

          {me?.role === "admin" && (
            <>
              <div className="border-t border-line-soft my-2" />
              <Link
                href="/admin/users"
                className="font-mono text-[9px] text-accent uppercase tracking-widest hover:underline"
              >
                Admin dashboard →
              </Link>
            </>
          )}

          <div className="border-t border-line-soft my-2" />
          <button
            onClick={() => signOut()}
            className="font-mono text-[11px] text-danger hover:underline"
          >
            Sign out
          </button>
        </div>
      )}
    </div>
  );
}
