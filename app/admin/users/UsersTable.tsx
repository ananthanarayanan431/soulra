"use client";
import { useState } from "react";
import { updateAdminUser, type AdminUser } from "@/lib/api";

export function UsersTable({ users: initialUsers }: { users: AdminUser[] }) {
  const [users, setUsers] = useState(initialUsers);
  const [savingId, setSavingId] = useState<string | null>(null);

  async function handleLimitChange(userId: string, value: string) {
    const tokenLimit = Number(value);
    if (!Number.isFinite(tokenLimit) || tokenLimit < 0) return;
    setSavingId(userId);
    const updated = await updateAdminUser(userId, { token_limit: tokenLimit });
    if (updated) {
      setUsers(prev => prev.map(u => (u.id === userId ? updated : u)));
    }
    setSavingId(null);
  }

  async function handleRoleToggle(userId: string, currentRole: "user" | "admin") {
    const role = currentRole === "admin" ? "user" : "admin";
    setSavingId(userId);
    const updated = await updateAdminUser(userId, { role });
    if (updated) {
      setUsers(prev => prev.map(u => (u.id === userId ? updated : u)));
    }
    setSavingId(null);
  }

  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="text-left font-mono text-[10px] uppercase tracking-widest text-muted border-b border-line">
          <th className="py-2 pr-4">Email</th>
          <th className="py-2 pr-4">Name</th>
          <th className="py-2 pr-4">Role</th>
          <th className="py-2 pr-4">Joined</th>
          <th className="py-2 pr-4">Last login</th>
          <th className="py-2 pr-4">Tokens used / limit</th>
        </tr>
      </thead>
      <tbody>
        {users.map(u => {
          const pct = u.token_limit > 0 ? Math.min(100, Math.round((u.tokens_used / u.token_limit) * 100)) : 0;
          return (
            <tr key={u.id} className="border-b border-line-soft">
              <td className="py-2 pr-4">{u.email}</td>
              <td className="py-2 pr-4">{u.name ?? "—"}</td>
              <td className="py-2 pr-4">
                <button
                  onClick={() => handleRoleToggle(u.id, u.role)}
                  disabled={savingId === u.id}
                  className="font-mono text-[11px] uppercase tracking-wide border border-line rounded px-2 py-0.5 hover:bg-paper-alt disabled:opacity-50"
                >
                  {u.role}
                </button>
              </td>
              <td className="py-2 pr-4 font-mono text-[11px] text-muted">
                {new Date(u.created_at).toLocaleDateString()}
              </td>
              <td className="py-2 pr-4 font-mono text-[11px] text-muted">
                {u.last_login_at ? new Date(u.last_login_at).toLocaleString() : "never"}
              </td>
              <td className="py-2 pr-4">
                <div className="flex items-center gap-2">
                  <div className="w-24 h-1.5 bg-line-soft rounded overflow-hidden">
                    <div className="h-full bg-accent" style={{ width: `${pct}%` }} />
                  </div>
                  <span className="font-mono text-[11px] text-muted">{u.tokens_used.toLocaleString()}</span>
                  <span className="font-mono text-[11px] text-muted">/</span>
                  <input
                    type="number"
                    defaultValue={u.token_limit}
                    onBlur={e => handleLimitChange(u.id, e.target.value)}
                    disabled={savingId === u.id}
                    className="w-24 font-mono text-[11px] border border-line rounded px-1 py-0.5 bg-paper"
                  />
                </div>
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
