const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface Conversation {
  id: string;
  thread_id: string;
  situation: string;
  clarify_q: string | null;
  created_at: string;
  action_steps: { step_number: number; title: string; body: string }[];
}

export async function listConversations(limit = 6): Promise<Conversation[]> {
  try {
    const res = await fetch(`${BASE}/api/v1/conversations?limit=${limit}`, {
      cache: "no-store",
    });
    if (!res.ok) return [];
    const json = await res.json();
    return (json.data ?? []) as Conversation[];
  } catch {
    return [];
  }
}

export function formatRelativeDate(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 60) return `${mins} min ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs} hr ago`;
  const days = Math.floor(hrs / 24);
  if (days === 1) return "yesterday";
  if (days < 14) return `${days} days ago`;
  const weeks = Math.floor(days / 7);
  return `${weeks} wk ago`;
}
