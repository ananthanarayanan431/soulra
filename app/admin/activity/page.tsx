import { listLoginEvents } from "@/lib/api";

export default async function AdminActivityPage() {
  const { items, total } = await listLoginEvents(100, 0);

  return (
    <div>
      <h1 className="font-serif text-2xl text-ink mb-1">Login activity</h1>
      <p className="font-mono text-[11px] text-muted mb-6">{total} events</p>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left font-mono text-[10px] uppercase tracking-widest text-muted border-b border-line">
            <th className="py-2 pr-4">User</th>
            <th className="py-2 pr-4">Event</th>
            <th className="py-2 pr-4">IP address</th>
            <th className="py-2 pr-4">User agent</th>
            <th className="py-2 pr-4">When</th>
          </tr>
        </thead>
        <tbody>
          {items.map(e => (
            <tr key={e.id} className="border-b border-line-soft">
              <td className="py-2 pr-4">{e.user_email}</td>
              <td className="py-2 pr-4 font-mono text-[11px] uppercase">{e.event_type}</td>
              <td className="py-2 pr-4 font-mono text-[11px] text-muted">{e.ip_address ?? "—"}</td>
              <td className="py-2 pr-4 font-mono text-[11px] text-muted truncate max-w-[240px]">{e.user_agent ?? "—"}</td>
              <td className="py-2 pr-4 font-mono text-[11px] text-muted">{new Date(e.created_at).toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
