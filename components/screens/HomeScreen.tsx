import Link from "next/link";
import { Sidebar } from "@/components/layout";
import { Chip } from "@/components/ui";
import { SituationInput } from "@/components/home/SituationInput";
import { listConversations, formatRelativeDate } from "@/lib/api";

export async function HomeScreen() {
  const conversations = await listConversations(3);

  return (
    <div className="flex h-screen bg-paper overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-auto">

        {/* greeting strip */}
        <div className="px-10 pt-8 pb-6 border-b border-line flex justify-between items-end">
          <div>
            <div className="font-mono text-[10px] text-muted uppercase tracking-widest">
              Soulra · wisdom companion
            </div>
            <div className="font-serif text-[36px] leading-tight mt-1.5">
              What&apos;s on your mind?
            </div>
            <div className="text-sm text-muted mt-2 max-w-[580px] leading-relaxed">
              Bring a situation, question, or weight you&apos;re carrying. The traditions will meet you there.
            </div>
          </div>
          <Link
            href="/journal"
            className="inline-flex items-center justify-center rounded-full border border-ink font-sans font-medium text-xs px-3 py-1.5 hover:bg-ink/5 transition-colors"
          >
            ◇ Open journal
          </Link>
        </div>

        {/* main grid */}
        <div className="px-10 py-6 grid grid-cols-[1.4fr_1fr] gap-5">

          {/* primary CTA */}
          <div className="col-span-2 border border-ink rounded-xl p-6 bg-paper-alt">
            <div className="font-mono text-[10px] text-accent uppercase tracking-widest mb-1.5">
              what is asking for your attention today?
            </div>
            <SituationInput />
            <div className="flex flex-wrap gap-1.5 mt-3.5 items-center">
              <span className="font-mono text-[10px] text-muted mr-1">or try:</span>
              <Chip onClick={undefined}>&ldquo;I keep saying yes when I mean no&rdquo;</Chip>
              <Chip onClick={undefined}>&ldquo;I&rsquo;m carrying grief that won&rsquo;t move&rdquo;</Chip>
              <Chip onClick={undefined}>&ldquo;Who am I outside this role?&rdquo;</Chip>
            </div>
          </div>

          {/* today's teaching */}
          <div className="border border-ink rounded-xl bg-ink text-paper p-6">
            <div className="font-mono text-[10px] text-accent-soft uppercase tracking-widest mb-2">
              a teaching to carry · Stoic
            </div>
            <div className="font-serif text-2xl leading-[1.35] italic">
              &ldquo;You always own the option of having no opinion.&rdquo;
            </div>
            <div className="font-mono text-[10px] text-accent-soft mt-2.5">
              ↳ Marcus Aurelius · Meditations 6.13
            </div>
            <div className="text-sm text-[#cdc6b8] leading-[1.7] mt-3.5">
              Today&apos;s only practice: pause for one breath before answering the next request.
            </div>
            <div className="flex gap-2 mt-4">
              <Link href="/chat?q=I%20keep%20saying%20yes%20when%20I%20mean%20no">
                <button className="text-xs border border-accent-soft text-accent-soft rounded-full px-3 py-1.5">
                  Explore this →
                </button>
              </Link>
              <button className="text-xs border border-[#3a352d] text-accent-soft rounded-full px-3 py-1.5">
                ◇ Save
              </button>
            </div>
          </div>

          {/* recent hint / placeholder */}
          <div className="border border-ink rounded-xl p-6 bg-paper">
            <div className="font-mono text-[10px] text-accent uppercase tracking-widest mb-2">
              from the traditions
            </div>
            <div className="font-serif text-[19px] leading-[1.4] italic">
              &ldquo;The yes that secures will resent itself.&rdquo;
            </div>
            <div className="font-mono text-[10px] text-muted mt-2">
              ↳ Bhagavad Gita 2.47
            </div>
            <div className="text-sm text-muted leading-[1.6] mt-3">
              Has this shown up in your week? Sit with it, or bring a new question.
            </div>
            <div className="flex gap-2 mt-4">
              <Link
                href="/chat?q=I%20keep%20saying%20yes%20to%20things%20I%20don%27t%20want%20to%20do"
                className="inline-flex items-center justify-center rounded-full border border-ink font-sans font-medium text-xs px-3 py-1.5 bg-ink text-paper hover:bg-ink/90 transition-colors"
              >
                Sit with this
              </Link>
            </div>
          </div>

          {/* recent conversations */}
          <div className="col-span-2 border border-line rounded-xl p-5 bg-paper">
            <div className="flex justify-between items-center mb-3">
              <div className="font-mono text-[10px] text-muted uppercase tracking-widest">
                recent conversations
              </div>
              <span className="font-mono text-[10px] text-accent">see all ↗</span>
            </div>

            {conversations.length > 0 ? (
              <div className="grid grid-cols-3 gap-3">
                {conversations.map(c => (
                  <Link key={c.id} href={`/chat?q=${encodeURIComponent(c.situation)}`}>
                    <div className="border border-line rounded-lg p-3 bg-paper-alt hover:border-ink transition-colors cursor-pointer">
                      <div className="font-serif text-[15px] leading-[1.35] italic">
                        &ldquo;{c.situation.slice(0, 60)}{c.situation.length > 60 ? "…" : ""}&rdquo;
                      </div>
                      <div className="flex justify-between items-center mt-2.5">
                        <span className="font-mono text-[9px] text-muted">
                          {formatRelativeDate(c.created_at)}
                        </span>
                        {c.clarify_q && (
                          <Chip className="text-[9px] px-2 py-0.5">reflected</Chip>
                        )}
                      </div>
                    </div>
                  </Link>
                ))}
              </div>
            ) : (
              <div className="text-sm text-muted text-center py-6">
                No conversations yet. Start one above.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
