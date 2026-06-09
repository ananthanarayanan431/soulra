const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface ConversationTraditionCard {
  card_order: number;
  tradition: string;
  author: string;
  quote: string;
  citation: string;
  analysis: string;
  source_passage: string;
}

export interface Conversation {
  id: string;
  thread_id: string;
  situation: string;
  clarify_q: string | null;
  clarify_ans: string | null;
  created_at: string;
  action_steps: { step_number: number; title: string; body: string }[];
  tradition_cards: ConversationTraditionCard[];
}

export async function getConversation(id: string): Promise<Conversation | null> {
  try {
    const res = await fetch(`${BASE}/api/v1/conversations/${id}`, { cache: "no-store" });
    if (!res.ok) return null;
    const json = await res.json();
    return (json.data ?? null) as Conversation | null;
  } catch {
    return null;
  }
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

export interface Tradition {
  slug: string;
  name: string;
  origin: string;
  era: string;
  sources: number;
  passages: number;
  selected: boolean;
  description?: string;
}

export interface TraditionsData {
  traditions: Tradition[];
  total_sources: number;
  total_passages: number;
}

export async function listTraditions(era?: string): Promise<TraditionsData> {
  const params = era && era !== "all" ? `?era=${encodeURIComponent(era)}` : "";
  try {
    const res = await fetch(`${BASE}/api/v1/traditions${params}`, { cache: "no-store" });
    if (!res.ok) return { traditions: [], total_sources: 0, total_passages: 0 };
    const json = await res.json();
    return (json.data ?? { traditions: [], total_sources: 0, total_passages: 0 }) as TraditionsData;
  } catch {
    return { traditions: [], total_sources: 0, total_passages: 0 };
  }
}

export async function updateTraditionPreferences(selected: string[]): Promise<void> {
  await fetch(`${BASE}/api/v1/traditions/preferences`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ selected }),
  });
}

export async function listEras(): Promise<string[]> {
  try {
    const res = await fetch(`${BASE}/api/v1/eras`, { cache: "no-store" });
    if (!res.ok) return [];
    const json = await res.json();
    return (json.data ?? []) as string[];
  } catch {
    return [];
  }
}

export interface TraditionInput {
  name: string;
  origin: string;
  era: string;
  slug?: string;
  description?: string;
}

export async function createTradition(body: TraditionInput): Promise<Tradition> {
  const res = await fetch(`${BASE}/api/v1/traditions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const json = await res.json().catch(() => ({}));
    throw new Error(json?.error?.message ?? `HTTP ${res.status}`);
  }
  const json = await res.json();
  return json.data as Tradition;
}

export async function updateTradition(slug: string, body: Partial<TraditionInput>): Promise<Tradition> {
  const res = await fetch(`${BASE}/api/v1/traditions/${encodeURIComponent(slug)}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const json = await res.json().catch(() => ({}));
    throw new Error(json?.error?.message ?? `HTTP ${res.status}`);
  }
  const json = await res.json();
  return json.data as Tradition;
}

export async function deleteTradition(slug: string): Promise<void> {
  const res = await fetch(`${BASE}/api/v1/traditions/${encodeURIComponent(slug)}`, { method: "DELETE" });
  if (!res.ok) {
    const json = await res.json().catch(() => ({}));
    throw new Error(json?.error?.message ?? `HTTP ${res.status}`);
  }
}

export interface PracticeDay {
  id: string;
  day_number: number;
  day_label: string;
  task_title: string;
  task_body: string;
  morning_quote: string;
  morning_author: string;
  morning_citation: string;
  morning_analysis: string;
  evening_prompt: string;
  reflection_text: string | null;
  completed: boolean;
  state: "done" | "today" | "future";
}

export interface PracticeArc {
  id: string;
  theme: string;
  status: string;
  current_day: number;
  days_into_arc: string;
  created_at: string;
  days: PracticeDay[];
}

export async function getActivePractice(): Promise<PracticeArc | null> {
  try {
    const res = await fetch(`${BASE}/api/v1/practice/active`, { cache: "no-store" });
    if (!res.ok) return null;
    const json = await res.json();
    return (json.data ?? null) as PracticeArc | null;
  } catch {
    return null;
  }
}

export async function completeDay(arcId: string, dayNumber: number): Promise<PracticeArc | null> {
  try {
    const res = await fetch(`${BASE}/api/v1/practice/${arcId}/days/${dayNumber}/complete`, {
      method: "PATCH",
    });
    if (!res.ok) return null;
    const json = await res.json();
    return (json.data ?? null) as PracticeArc | null;
  } catch {
    return null;
  }
}

export async function saveReflection(arcId: string, dayNumber: number, text: string): Promise<void> {
  await fetch(`${BASE}/api/v1/practice/${arcId}/days/${dayNumber}/reflect`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
}

export interface JournalEntry {
  id: string;
  text: string;
  quote: string | null;
  tradition: string | null;
  author: string | null;
  citation: string | null;
  analysis: string | null;
  tags: string[];
  applied: boolean;
  applied_at: string | null;
  saved_at: string;
  conversation_id: string | null;
}

export interface JournalStats {
  total: number;
  applied_this_month: number;
  last_applied_days_ago: number | null;
}

export interface TagCount {
  name: string;
  count: number;
}

export interface JournalData {
  entries: JournalEntry[];
  stats: JournalStats;
  tag_counts: TagCount[];
  tradition_counts: TagCount[];
  revisit: JournalEntry | null;
}

export async function getJournal(tag?: string): Promise<JournalData> {
  const empty: JournalData = { entries: [], stats: { total: 0, applied_this_month: 0, last_applied_days_ago: null }, tag_counts: [], tradition_counts: [], revisit: null };
  try {
    const params = tag && tag !== "all" ? `?tag=${encodeURIComponent(tag)}` : "";
    const res = await fetch(`${BASE}/api/v1/journal${params}`, { cache: "no-store" });
    if (!res.ok) return empty;
    const json = await res.json();
    return (json.data ?? empty) as JournalData;
  } catch {
    return empty;
  }
}

export async function saveJournalEntry(body: {
  text: string;
  quote?: string;
  tradition?: string;
  author?: string;
  citation?: string;
  analysis?: string;
  tags?: string[];
  conversation_id?: string;
}): Promise<JournalEntry | null> {
  try {
    const res = await fetch(`${BASE}/api/v1/journal`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) return null;
    const json = await res.json();
    return (json.data ?? null) as JournalEntry | null;
  } catch {
    return null;
  }
}

export async function patchJournalEntry(id: string, body: { applied?: boolean; tags?: string[] }): Promise<JournalEntry | null> {
  try {
    const res = await fetch(`${BASE}/api/v1/journal/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) return null;
    const json = await res.json();
    return (json.data ?? null) as JournalEntry | null;
  } catch {
    return null;
  }
}

export async function deleteJournalEntry(id: string): Promise<void> {
  await fetch(`${BASE}/api/v1/journal/${id}`, { method: "DELETE" });
}

export interface IngestJob {
  job_id: string;
  status: "processing" | "done" | "failed";
  filename?: string;
  chunks_created?: number;
  error?: string;
}

export async function ingestPdf(formData: FormData): Promise<IngestJob | null> {
  try {
    const res = await fetch(`${BASE}/api/v1/ingest/pdf`, {
      method: "POST",
      body: formData,
    });
    if (!res.ok) {
      const json = await res.json().catch(() => ({}));
      throw new Error(json?.error?.message ?? `HTTP ${res.status}`);
    }
    const json = await res.json();
    return json.data as IngestJob;
  } catch (e) {
    throw e;
  }
}

export async function ingestUrl(formData: FormData): Promise<IngestJob | null> {
  try {
    const res = await fetch(`${BASE}/api/v1/ingest/url`, { method: "POST", body: formData });
    if (!res.ok) {
      const json = await res.json().catch(() => ({}));
      throw new Error(json?.detail ?? json?.error?.message ?? `HTTP ${res.status}`);
    }
    return (await res.json()).data as IngestJob;
  } catch (e) { throw e; }
}

export async function ingestText(formData: FormData): Promise<IngestJob | null> {
  try {
    const res = await fetch(`${BASE}/api/v1/ingest/text`, { method: "POST", body: formData });
    if (!res.ok) {
      const json = await res.json().catch(() => ({}));
      throw new Error(json?.detail ?? json?.error?.message ?? `HTTP ${res.status}`);
    }
    return (await res.json()).data as IngestJob;
  } catch (e) { throw e; }
}

export async function ingestYoutube(formData: FormData): Promise<IngestJob | null> {
  try {
    const res = await fetch(`${BASE}/api/v1/ingest/youtube`, { method: "POST", body: formData });
    if (!res.ok) {
      const json = await res.json().catch(() => ({}));
      throw new Error(json?.detail ?? json?.error?.message ?? `HTTP ${res.status}`);
    }
    return (await res.json()).data as IngestJob;
  } catch (e) { throw e; }
}

export async function getIngestJob(jobId: string): Promise<IngestJob | null> {
  try {
    const res = await fetch(`${BASE}/api/v1/ingest/jobs/${jobId}`, { cache: "no-store" });
    if (!res.ok) return null;
    const json = await res.json();
    return json.data as IngestJob;
  } catch {
    return null;
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
