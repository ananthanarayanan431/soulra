import { listAdminUsers } from "@/lib/api";
import { UsersTable } from "./UsersTable";

export default async function AdminUsersPage() {
  const { items, total } = await listAdminUsers(100, 0);

  return (
    <div>
      <h1 className="font-serif text-2xl text-ink mb-1">Users</h1>
      <p className="font-mono text-[11px] text-muted mb-6">{total} total</p>
      <UsersTable users={items} />
    </div>
  );
}
