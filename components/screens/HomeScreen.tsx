import Link from "next/link";
import { Sidebar } from "@/components/layout";
import {
  listConversations,
  getActivePractice,
  getMe,
  formatRelativeDate,
} from "@/lib/api";
import type { Conversation, PracticeDay, MeData } from "@/lib/api";

function TodayPractice({ today }: { today: PracticeDay }) {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <div className="font-mono text-[10px] text-muted uppercase tracking-widest mb-3">
          morning · today&apos;s practice
        </div>
        <div className="font-serif text-[22px] leading-[1.4] italic">
          &ldquo;{today.morning_quote}&rdquo;
        </div>
        <div className="font-mono text-[10px] text-accent mt-2">
          &darr; {today.morning_author} &middot; {today.morning_citation}
        </div>
        <p className="text-[13px] text-muted leading-[1.7] mt-3 max-w-[600px]">
          {today.morning_analysis}
        </p>
      </div>

      <div className="border-t border-line pt-5">
        <div className="font-mono text-[10px] text-muted uppercase tracking-widest mb-2">
          evening · reflection
        </div>
        <div className="font-serif text-[18px] leading-[1.4] italic text-ink">
          {today.evening_prompt}
        </div>
      </div>

      <div className="flex gap-5 items-center">
        <Link href="/chat" className="font-mono text-[11px] text-accent hover:underline">
          Begin a new conversation →
        </Link>
        <Link href="/daily" className="font-mono text-[11px] text-muted hover:text-ink transition-colors">
          See this week →
        </Link>
      </div>
    </div>
  );
}

function EmptyPractice() {
  return (
    <div className="flex flex-col gap-4">
      <p className="text-[14px] text-muted leading-relaxed max-w-[480px]">
        Complete a conversation to begin your 7-day practice thread — morning teachings
        drawn from what the traditions said to you, evening questions to close the day.
      </p>
      <Link href="/chat" className="font-mono text-[11px] text-accent hover:underline">
        Begin a conversation →
      </Link>
    </div>
  );
}

function AccountSummary({ me }: { me: MeData }) {
  const tokensLeft = Math.max(0, me.token_limit - me.tokens_used);
  const pct = me.token_limit > 0
    ? Math.min(100, (me.tokens_used / me.token_limit) * 100)
    : 0;

  return (
    <div className="border border-line rounded-xl px-5 py-4 bg-paper-alt flex flex-col gap-2 w-[260px] flex-shrink-0">
      <div className="font-mono text-[9px] text-muted uppercase tracking-widest">
        Token usage
      </div>
      <div className="h-1.5 rounded-full bg-paper overflow-hidden">
        <div className="h-full bg-accent" style={{ width: `${pct}%` }} />
      </div>
      <div className="font-mono text-[10px] text-muted">
        {tokensLeft.toLocaleString()} tokens left
      </div>

      <div className="border-t border-line-soft my-1" />
      <div className="font-mono text-[10px] text-muted">
        First login {formatRelativeDate(me.created_at)}
      </div>
      {me.last_login_at && (
        <div className="font-mono text-[10px] text-muted">
          Last login {formatRelativeDate(me.last_login_at)}
        </div>
      )}
    </div>
  );
}

function RecentConversations({ conversations }: { conversations: Conversation[] }) {
  if (conversations.length === 0) return null;

  return (
    <div>
      <div className="font-mono text-[10px] text-muted uppercase tracking-widest mb-3">
        recent conversations
      </div>
      <div className="grid grid-cols-3 gap-3">
        {conversations.map(c => (
          <Link key={c.id} href={`/chat?id=${c.id}`}>
            <div className="border border-line rounded-xl p-4 bg-paper-alt hover:border-ink transition-colors cursor-pointer h-full">
              <div className="font-serif text-[14px] leading-snug italic">
                &ldquo;{c.situation.slice(0, 65)}{c.situation.length > 65 ? "…" : ""}&rdquo;
              </div>
              <div className="flex justify-between items-center mt-3">
                <span className="font-mono text-[9px] text-muted">
                  {formatRelativeDate(c.created_at)}
                </span>
                <span className="font-mono text-[9px] text-accent">
                  {c.tradition_cards.length} voice{c.tradition_cards.length !== 1 ? "s" : ""}
                </span>
              </div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}

export async function HomeScreen() {
  const [conversations, arc, me] = await Promise.all([
    listConversations(3),
    getActivePractice(),
    getMe(),
  ]);

  const today = arc
    ? (arc.days.find(d => d.state === "today") ?? arc.days[arc.current_day - 1])
    : null;

  const dateLabel = new Date().toLocaleDateString("en-US", {
    weekday: "long",
    month: "long",
    day: "numeric",
  }).toUpperCase();

  return (
    <div className="flex h-screen bg-paper overflow-hidden">
      <Sidebar />

      <div className="flex-1 overflow-auto px-10 py-10">
        <div className="flex items-start justify-between gap-8 mb-5">
          <div className="font-mono text-[10px] text-muted uppercase tracking-widest pt-1">
            {dateLabel}
          </div>
          {me && <AccountSummary me={me} />}
        </div>

        <div className="font-serif text-[36px] leading-[1.25] mb-8 max-w-[560px]">
          What is asking for your attention today?
        </div>

        <div className="border-t border-line pt-7 mb-10">
          {today ? <TodayPractice today={today} /> : <EmptyPractice />}
        </div>

        <RecentConversations conversations={conversations} />
      </div>
    </div>
  );
}
