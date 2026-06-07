import { Suspense } from "react";
import { ConversationScreen } from "@/components/screens/ConversationScreen";

function Loading() {
  return (
    <div className="flex h-screen items-center justify-center bg-paper">
      <div className="font-serif text-[20px] text-muted italic">Loading…</div>
    </div>
  );
}

export default function ChatPage() {
  return (
    <Suspense fallback={<Loading />}>
      <ConversationScreen />
    </Suspense>
  );
}
