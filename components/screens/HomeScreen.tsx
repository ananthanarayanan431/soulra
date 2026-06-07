import Link from "next/link";
import { Sidebar } from "@/components/layout";
import { Chip } from "@/components/ui";
import { SituationInput } from "@/components/home/SituationInput";
import {
  listConversations,
  listTraditions,
  getActivePractice,
  formatRelativeDate,
} from "@/lib/api";
import type { Conversation, Tradition, PracticeArc } from "@/lib/api";

const FLOW_STEPS = [
  {
    n: "01",
    glyph: "◎",
    title: "Bring a situation",
    body: "Not a query — a weight. Something you're carrying, avoiding, or trying to understand. Soulra isn't a search engine; it's a conversation.",
    href: "/chat",
    cta: "Start talking →",
  },
  {
    n: "02",
    glyph: "◯",
    title: "The traditions respond",
    body: "Soulra searches across Stoic, Vedanta, Buddhist, Sufi and other lineages — not to pick one answer, but to show how different wisdom sees the same knot.",
    href: "/traditions",
    cta: "Choose your room →",
  },
  {
    n: "03",
    glyph: "◻",
    title: "A 7-day thread begins",
    body: "Every conversation seeds a week of practice. Each morning a teaching arrives. Each evening a question. No streaks — the thread holds even when you miss a day.",
    href: "/daily",
    cta: "See today's practice →",
  },
  {
    n: "04",
    glyph: "◇",
    title: "Wisdom accumulates",
    body: "Save what stays with you. Tag it. Mark when it actually shows up in a real moment. Over time your journal becomes a record of who you're becoming.",
    href: "/journal",
    cta: "Open your journal →",
  },
];

const PROMPT_CHIPS = [
  "I keep saying yes when I mean no",
  "I'm carrying grief that won't move",
  "Who am I outside this role?",
];

function FlowStep({
  step,
  last,
}: {
  step: typeof FLOW_STEPS[number];
  last: boolean;
}) {
  return (
    <div className="flex gap-4 group">
      {/* spine */}
      <div className="flex flex-col items-center gap-0">
        <div className="w-8 h-8 rounded-full border border-ink flex items-center justify-center font-mono text-[11px] text-ink flex-shrink-0">
          {step.glyph}
        </div>
        {!last && <div className="w-px flex-1 bg-line mt-1 min-h-[32px]" />}
      </div>

      {/* content */}
      <div className={`pb-7 ${last ? "" : ""}`}>
        <div className="flex items-center gap-2 mb-1">
          <span className="font-mono text-[9px] text-muted tracking-widest">{step.n}</span>
          <span className="font-serif text-[18px] leading-tight">{step.title}</span>
        </div>
        <p className="text-[13px] text-muted leading-[1.7] max-w-[320px]">{step.body}</p>
        <Link
          href={step.href}
          className="font-mono text-[10px] text-accent mt-2 inline-block hover:underline"
        >
          {step.cta}
        </Link>
      </div>
    </div>
  );
}

function TraditionsPanel({ traditions }: { traditions: Tradition[] }) {
  const selected = traditions.filter(t => t.selected);
  return (
    <div className="border border-line rounded-xl p-5 bg-paper-alt h-full">
      <div className="font-mono text-[10px] text-muted uppercase tracking-widest mb-3">
        voices in your room
      </div>
      {selected.length === 0 ? (
        <p className="text-[13px] text-muted italic">No traditions selected yet.</p>
      ) : (
        <div className="flex flex-wrap gap-1.5 mb-4">
          {selected.map(t => (
            <span
              key={t.slug}
              className="border border-ink rounded-full px-2.5 py-1 font-mono text-[11px] text-ink"
            >
              {t.name}
            </span>
          ))}
        </div>
      )}
      <p className="text-[12px] text-muted leading-[1.6]">
        These lineages are searched with every conversation. You can swap them any time —
        adding a new voice changes the texture of every future response.
      </p>
      <Link
        href="/traditions"
        className="font-mono text-[10px] text-accent mt-3 inline-block hover:underline"
      >
        Edit your room →
      </Link>
    </div>
  );
}

function PracticePanel({ arc }: { arc: PracticeArc | null }) {
  if (!arc) {
    return (
      <div className="border border-dashed border-line rounded-xl p-5 flex flex-col justify-between h-full">
        <div>
          <div className="font-mono text-[10px] text-muted uppercase tracking-widest mb-2">
            your practice arc
          </div>
          <div className="font-serif text-[18px] leading-snug italic text-muted">
            No active practice yet.
          </div>
          <p className="text-[12px] text-muted mt-2 leading-[1.6]">
            After your first conversation, Soulra builds a 7-day practice thread — morning teachings
            drawn from what the traditions said to you, evening questions to close the day.
          </p>
        </div>
        <Link
          href="/chat"
          className="font-mono text-[10px] text-accent mt-4 inline-block hover:underline"
        >
          Start a conversation to begin →
        </Link>
      </div>
    );
  }

  const today = arc.days.find(d => d.state === "today") ?? arc.days[arc.current_day - 1];

  return (
    <div className="border border-ink rounded-xl p-5 bg-paper flex flex-col justify-between h-full">
      <div>
        <div className="font-mono text-[10px] text-muted uppercase tracking-widest mb-1">
          your practice · {arc.days_into_arc}
        </div>
        <div className="font-serif text-[18px] leading-snug italic mt-1">
          {arc.theme.slice(0, 80)}{arc.theme.length > 80 ? "…" : ""}
        </div>

        {today && (
          <div className="mt-4 border-t border-line pt-3">
            <div className="font-mono text-[9px] text-muted uppercase tracking-widest mb-1">
              today · {today.day_label}
            </div>
            <div className="text-[13px] text-ink">{today.task_title}</div>
            {today.morning_quote && (
              <div className="font-serif text-[13px] text-muted italic mt-1.5 leading-snug">
                &ldquo;{today.morning_quote.slice(0, 100)}{today.morning_quote.length > 100 ? "…" : ""}&rdquo;
              </div>
            )}
          </div>
        )}
      </div>

      <Link
        href="/daily"
        className="font-mono text-[10px] text-accent mt-4 inline-block hover:underline"
      >
        Open today's practice →
      </Link>
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
  const [conversations, { traditions }, arc] = await Promise.all([
    listConversations(3),
    listTraditions(),
    getActivePractice(),
  ]);

  return (
    <div className="flex h-screen bg-paper overflow-hidden">
      <Sidebar />

      <div className="flex-1 flex flex-col overflow-auto">

        {/* hero */}
        <div className="px-10 pt-10 pb-7 border-b border-line">
          <div className="font-mono text-[10px] text-muted uppercase tracking-widest mb-1.5">
            Soulra · wisdom companion
          </div>
          <div className="font-serif text-[42px] leading-[1.2] max-w-[640px]">
            Ancient wisdom,<br />applied to what is alive in you now.
          </div>
          <p className="text-[14px] text-muted mt-3 max-w-[560px] leading-relaxed">
            Bring a situation, question, or weight you&apos;re carrying.
            Soulra draws from Stoic, Vedanta, Buddhist and other lineages —
            not to give you an answer, but to show you how the traditions see your knot.
          </p>
        </div>

        <div className="px-10 py-7 flex flex-col gap-8">

          {/* conversation input */}
          <div className="border border-ink rounded-xl p-6 bg-paper-alt">
            <div className="font-mono text-[10px] text-accent uppercase tracking-widest mb-3">
              what is asking for your attention today?
            </div>
            <SituationInput />
            <div className="flex flex-wrap gap-1.5 mt-3 items-center">
              <span className="font-mono text-[10px] text-muted mr-1">or try:</span>
              {PROMPT_CHIPS.map(chip => (
                <Chip key={chip}>&ldquo;{chip}&rdquo;</Chip>
              ))}
            </div>
          </div>

          {/* how soulra works */}
          <div>
            <div className="font-mono text-[10px] text-muted uppercase tracking-widest mb-5">
              how soulra works
            </div>
            <div className="grid grid-cols-2 gap-x-12">
              <div>
                {FLOW_STEPS.slice(0, 2).map((step, i) => (
                  <FlowStep key={step.n} step={step} last={i === 1} />
                ))}
              </div>
              <div>
                {FLOW_STEPS.slice(2).map((step, i) => (
                  <FlowStep key={step.n} step={step} last={i === 1} />
                ))}
              </div>
            </div>
          </div>

          {/* traditions + practice side by side */}
          <div className="grid grid-cols-2 gap-5">
            <TraditionsPanel traditions={traditions} />
            <PracticePanel arc={arc} />
          </div>

          {/* recent conversations */}
          <RecentConversations conversations={conversations} />

        </div>
      </div>
    </div>
  );
}
