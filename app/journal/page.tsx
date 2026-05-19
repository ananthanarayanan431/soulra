import { Sidebar } from "@/components/layout";

export default function JournalPage() {
  return (
    <div className="flex h-screen bg-paper overflow-hidden">
      <Sidebar />
      <main className="flex-1 overflow-auto p-10">
        <div className="font-mono text-[10px] text-muted uppercase tracking-widest">your journal</div>
        <div className="font-serif text-4xl mt-2">Wisdom you've kept.</div>
      </main>
    </div>
  );
}
