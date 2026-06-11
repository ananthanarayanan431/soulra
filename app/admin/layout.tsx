import { redirect } from "next/navigation";
import Link from "next/link";
import { getMe } from "@/lib/api";

const ADMIN_NAV = [
  { href: "/admin/users", label: "Users" },
  { href: "/admin/activity", label: "Login activity" },
  { href: "/admin/usage", label: "Token usage" },
];

export default async function AdminLayout({ children }: { children: React.ReactNode }) {
  const me = await getMe();
  if (!me || me.role !== "admin") {
    redirect("/home");
  }

  return (
    <div className="flex min-h-screen">
      <aside className="w-[200px] border-r border-line bg-paper-alt flex-shrink-0 px-4 py-5">
        <div className="font-mono text-[10px] text-muted uppercase tracking-widest mb-3">Admin</div>
        <nav className="flex flex-col gap-1">
          {ADMIN_NAV.map(item => (
            <Link
              key={item.href}
              href={item.href}
              className="px-2.5 py-2 rounded-md text-sm text-ink border border-transparent hover:bg-paper/50"
            >
              {item.label}
            </Link>
          ))}
        </nav>
        <div className="mt-6">
          <Link href="/home" className="font-mono text-[10px] text-muted uppercase tracking-widest">
            ← Back to app
          </Link>
        </div>
      </aside>
      <main className="flex-1 p-8">{children}</main>
    </div>
  );
}
