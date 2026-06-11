import { listTokenUsage } from "@/lib/api";

export default async function AdminUsagePage() {
  const { items, total } = await listTokenUsage(100, 0);

  return (
    <div>
      <h1 className="font-serif text-2xl text-ink mb-1">Token usage</h1>
      <p className="font-mono text-[11px] text-muted mb-6">{total} entries</p>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left font-mono text-[10px] uppercase tracking-widest text-muted border-b border-line">
            <th className="py-2 pr-4">User</th>
            <th className="py-2 pr-4">Model</th>
            <th className="py-2 pr-4">Prompt</th>
            <th className="py-2 pr-4">Completion</th>
            <th className="py-2 pr-4">Total</th>
            <th className="py-2 pr-4">When</th>
          </tr>
        </thead>
        <tbody>
          {items.map(u => (
            <tr key={u.id} className="border-b border-line-soft">
              <td className="py-2 pr-4">{u.user_email}</td>
              <td className="py-2 pr-4 font-mono text-[11px]">{u.model}</td>
              <td className="py-2 pr-4 font-mono text-[11px] text-muted">{u.prompt_tokens.toLocaleString()}</td>
              <td className="py-2 pr-4 font-mono text-[11px] text-muted">{u.completion_tokens.toLocaleString()}</td>
              <td className="py-2 pr-4 font-mono text-[11px]">{u.total_tokens.toLocaleString()}</td>
              <td className="py-2 pr-4 font-mono text-[11px] text-muted">{new Date(u.created_at).toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
