import { getJournal } from "@/lib/api";
import { JournalClient } from "@/components/screens/JournalClient";
import { Sidebar } from "@/components/layout";
import { Squiggle } from "@/components/ui";

function EmptyState() {
  return (
    <div className="flex h-screen bg-paper overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-auto px-[60px]">
        <div className="pt-[60px] pb-[30px] border-b border-line-soft">
          <div className="font-mono text-[10px] text-muted uppercase tracking-widest">your journal</div>
          <div className="font-serif text-[44px] leading-tight mt-2 italic">
            A place for wisdom
            <br />
            that has met you.
          </div>
          <Squiggle width={140} className="mt-4" />
        </div>
        <div className="pt-10 pb-[60px]">
          <p className="text-[15px] leading-[1.7] text-ink max-w-[460px]">
            Most chat apps treat saved messages like a graveyard. This isn&rsquo;t that.
            <br /><br />
            Your journal is the small library of teachings that stayed with you. Complete
            a conversation to begin — then save the wisdom that resonates.
          </p>
        </div>
      </div>
    </div>
  );
}

export default async function JournalPage() {
  const data = await getJournal();
  if (data.stats.total === 0) return <EmptyState />;
  return <JournalClient initialData={data} />;
}
