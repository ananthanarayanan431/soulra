import { Sidebar } from "@/components/layout";

export default function ChatPage() {
  return (
    <div className="flex h-screen bg-paper overflow-hidden">
      <Sidebar />
      <main className="flex-1 overflow-auto p-10">
        <div className="font-mono text-[10px] text-muted uppercase tracking-widest">conversation</div>
        <div className="font-serif text-4xl mt-2">What is asking for your attention?</div>
      </main>
    </div>
  );
}
