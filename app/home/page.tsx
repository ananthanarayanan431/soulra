import { Sidebar } from "@/components/layout";

export default function HomePage() {
  return (
    <div className="flex h-screen bg-paper overflow-hidden">
      <Sidebar />
      <main className="flex-1 overflow-auto p-10">
        <div className="font-mono text-[10px] text-muted uppercase tracking-widest">home · today</div>
        <div className="font-serif text-4xl mt-2">Welcome back.</div>
      </main>
    </div>
  );
}
