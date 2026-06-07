import { Suspense } from "react";
import { ConversationScreen } from "@/components/screens/ConversationScreen";
import { getConversation } from "@/lib/api";
import type { Conversation } from "@/lib/api";

function Loading() {
  return (
    <div className="flex h-screen items-center justify-center bg-paper">
      <div className="font-serif text-[20px] text-muted italic">Loading…</div>
    </div>
  );
}

export default async function ChatPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string; id?: string }>;
}) {
  const { q, id } = await searchParams;

  let loadedConversation: Conversation | null = null;
  if (id) {
    loadedConversation = await getConversation(id);
  }

  return (
    <Suspense fallback={<Loading />}>
      <ConversationScreen situation={q ?? null} loadedConversation={loadedConversation} />
    </Suspense>
  );
}
