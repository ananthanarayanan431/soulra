"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Sidebar } from "@/components/layout";
import { Button, Chip, Input } from "@/components/ui";
import { TraditionCard } from "@/components/conversation/TraditionCard";
import { ActionPlan } from "@/components/conversation/ActionPlan";
import { ClarifyingPause } from "@/components/conversation/ClarifyingPause";
import { useSoulraChat } from "@/hooks/useSoulraChat";
import { saveJournalEntry } from "@/lib/api";
import type { Conversation } from "@/lib/api";

const STATUS_LABELS: Record<string, string> = {
  intake:           "Understanding your situation…",
  retrieve:         "Searching wisdom traditions…",
  rerank:           "Refining passages…",
  grade_docs:       "Evaluating relevance…",
  rewrite_query:    "Deepening the search…",
  clarify:          "Preparing a question…",
  retrieve_refined: "Searching further…",
  rerank_refined:   "Refining results…",
  synthesize:       "Drawing from the traditions…",
};

function ThinkingIndicator({ node }: { node: string }) {
  return (
    <div className="flex gap-3.5">
      <div className="w-8 h-8 rounded-full border border-ink flex items-center justify-center font-serif text-sm flex-shrink-0">
        S
      </div>
      <div className="flex-1 pt-1">
        <div className="font-mono text-[10px] text-muted uppercase tracking-wide mb-1.5">Soulra</div>
        <div className="font-serif text-[17px] text-muted italic">
          {STATUS_LABELS[node] ?? "Consulting the traditions…"}
        </div>
      </div>
    </div>
  );
}

function UserBubble({ text }: { text: string }) {
  return (
    <div className="self-end max-w-[520px] px-4 py-3.5 bg-paper-alt border border-line rounded-[14px_14px_2px_14px] text-[14px] leading-relaxed">
      {text}
    </div>
  );
}

interface CompletedViewProps {
  situation: string;
  traditionCards: { tradition: string; author: string; quote: string; citation: string; analysis: string }[];
  actionSteps: { n: string; title: string; body: string }[];
  conversationId: string | null;
}

function CompletedView({ situation, traditionCards, actionSteps, conversationId }: CompletedViewProps) {
  async function handleSaveToJournal() {
    for (const card of traditionCards) {
      await saveJournalEntry({
        text: card.quote.slice(0, 120),
        quote: card.quote,
        tradition: card.tradition,
        author: card.author,
        citation: card.citation,
        analysis: card.analysis,
        conversation_id: conversationId ?? undefined,
      });
    }
  }
  return (
    <div className="flex h-screen bg-paper overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <div className="px-9 py-4 border-b border-line flex items-center justify-between flex-shrink-0">
          <div>
            <div className="font-serif text-[16px] font-medium truncate max-w-[520px]">
              &ldquo;{situation.slice(0, 70)}{situation.length > 70 ? "…" : ""}&rdquo;
            </div>
            <div className="font-mono text-[10px] text-muted mt-0.5">
              {traditionCards.length} tradition{traditionCards.length !== 1 ? "s" : ""} consulted
            </div>
          </div>
        </div>

        <div className="flex-1 overflow-auto px-9 py-8 flex flex-col gap-7 max-w-[820px] self-center w-full">
          <UserBubble text={situation} />

          {traditionCards.length > 0 && (
            <div className="flex gap-3.5">
              <div className="w-8 flex-shrink-0" />
              <div className="flex-1 flex flex-col gap-4">
                <p className="text-[14px] leading-[1.7] max-w-[640px]">
                  Here are perspectives from{" "}
                  {traditionCards.length} tradition{traditionCards.length !== 1 ? "s" : ""},
                  each rooted in its own lineage. They don&rsquo;t say the same thing — and that is the point.
                </p>

                {traditionCards.map((t, i) => (
                  <TraditionCard
                    key={i}
                    index={i + 1}
                    total={traditionCards.length}
                    tradition={t.tradition}
                    author={t.author}
                    quote={t.quote}
                    explanation={t.analysis}
                    citationBook={t.citation}
                    citationChapter=""
                    sourcePassage={t.source_passage}
                    initiallyExpanded={i === 0}
                  />
                ))}

                {actionSteps.length > 0 && (
                  <ActionPlan
                    steps={actionSteps.map(s => ({
                      number: s.n,
                      title: s.title,
                      body: s.body,
                    }))}
                    onSaveToJournal={handleSaveToJournal}
                  />
                )}

                <div className="flex justify-between items-center font-mono text-[10px] text-muted pt-1">
                  <span>
                    {traditionCards.length} sources &middot; grounded response
                  </span>
                  <span>was this grounded? &middot; &#128077; &middot; &#128078;</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

interface Props {
  situation: string | null;
  loadedConversation: Conversation | null;
}

export function ConversationScreen({ situation, loadedConversation }: Props) {
  const router = useRouter();
  const [reply, setReply] = useState("");

  const { state, sendClarification } = useSoulraChat(situation ?? "");
  const {
    phase,
    statusNode,
    clarifyQuestion,
    clarifyOptions,
    clarifyAnswer,
    traditionCards,
    actionSteps,
    error,
    conversationId,
  } = state;

  // After WS completes, replace URL with ?id= so refresh loads from API
  useEffect(() => {
    if (phase === "done" && conversationId) {
      router.replace(`/chat?id=${conversationId}`);
    }
  }, [phase, conversationId, router]);

  // Hard-refresh with ?id= — render the pre-fetched completed conversation
  if (loadedConversation) {
    return (
      <CompletedView
        situation={loadedConversation.situation}
        traditionCards={loadedConversation.tradition_cards.map(c => ({
          tradition: c.tradition,
          author: c.author,
          quote: c.quote,
          citation: c.citation,
          analysis: c.analysis,
        }))}
        actionSteps={loadedConversation.action_steps.map(s => ({
          n: String(s.step_number),
          title: s.title,
          body: s.body,
        }))}
        conversationId={loadedConversation.id}
      />
    );
  }

  async function handleSaveToJournal() {
    for (const card of traditionCards) {
      await saveJournalEntry({
        text: card.quote.slice(0, 120),
        quote: card.quote,
        tradition: card.tradition,
        author: card.author,
        citation: card.citation,
        analysis: card.analysis,
        conversation_id: conversationId ?? undefined,
      });
    }
  }

  // No situation — show entry input
  if (!situation) {
    const PROMPTS = [
      "I keep saying yes when I mean no",
      "I'm carrying grief that won't move",
      "Who am I outside this role?",
      "I can't stop replaying what happened",
    ];

    return (
      <div className="flex h-screen bg-paper overflow-hidden">
        <Sidebar />
        <div className="flex-1 flex flex-col items-center justify-center gap-6 px-10">
          <div className="font-serif text-[32px] leading-[1.3] text-center max-w-[500px]">
            What is asking for your attention today?
          </div>
          <div className="w-full max-w-[580px] flex flex-col gap-3">
            <Input
              big
              placeholder="Tell Soulra what's on your mind…"
              value={reply}
              onChange={setReply}
              onSubmit={() => {
                const trimmed = reply.trim();
                if (trimmed) router.push(`/chat?q=${encodeURIComponent(trimmed)}`);
              }}
            />
            <div className="flex flex-wrap gap-1.5 items-center">
              <span className="font-mono text-[10px] text-muted">or try:</span>
              {PROMPTS.map(p => (
                <Chip
                  key={p}
                  onClick={() => router.push(`/chat?q=${encodeURIComponent(p)}`)}
                >
                  &ldquo;{p}&rdquo;
                </Chip>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  const isActive = phase === "clarifying";
  const showInput = phase === "done" || phase === "clarifying";

  return (
    <div className="flex h-screen bg-paper overflow-hidden">
      <Sidebar />

      <div className="flex-1 flex flex-col overflow-hidden">
        {/* top bar */}
        <div className="px-9 py-4 border-b border-line flex items-center justify-between flex-shrink-0">
          <div>
            <div className="font-serif text-[16px] font-medium truncate max-w-[520px]">
              &ldquo;{situation.slice(0, 70)}{situation.length > 70 ? "…" : ""}&rdquo;
            </div>
            <div className="font-mono text-[10px] text-muted mt-0.5">
              {phase === "done"
                ? `${traditionCards.length} tradition${traditionCards.length !== 1 ? "s" : ""} consulted`
                : phase === "error"
                  ? "error"
                  : "…"}
            </div>
          </div>
          {phase === "done" && (
            <div className="flex gap-2">
              <Button small>◇ Save to journal</Button>
            </div>
          )}
        </div>

        {/* conversation thread */}
        <div className="flex-1 overflow-auto px-9 py-8 flex flex-col gap-7 max-w-[820px] self-center w-full">

          <UserBubble text={situation} />

          {(phase === "connecting" || phase === "thinking") && (
            <ThinkingIndicator node={statusNode} />
          )}

          {clarifyQuestion && (
            <ClarifyingPause
              question={clarifyQuestion}
              options={clarifyOptions}
              onSelect={isActive ? sendClarification : undefined}
            />
          )}

          {clarifyAnswer && <UserBubble text={clarifyAnswer} />}

          {phase === "responding" && <ThinkingIndicator node={statusNode} />}

          {traditionCards.length > 0 && (
            <div className="flex gap-3.5">
              <div className="w-8 flex-shrink-0" />
              <div className="flex-1 flex flex-col gap-4">
                {phase === "done" && (
                  <p className="text-[14px] leading-[1.7] max-w-[640px]">
                    Here are perspectives from{" "}
                    {traditionCards.length} tradition{traditionCards.length !== 1 ? "s" : ""},
                    each rooted in its own lineage. They don&rsquo;t say the same thing — and that is the point.
                  </p>
                )}

                {traditionCards.map((t, i) => (
                  <TraditionCard
                    key={i}
                    index={i + 1}
                    total={traditionCards.length}
                    tradition={t.tradition}
                    author={t.author}
                    quote={t.quote}
                    explanation={t.analysis}
                    citationBook={t.citation}
                    citationChapter=""
                    sourcePassage={t.source_passage}
                    initiallyExpanded={i === 0}
                  />
                ))}

                {actionSteps.length > 0 && (
                  <ActionPlan
                    steps={actionSteps.map(s => ({
                      number: s.n,
                      title: s.title,
                      body: s.body,
                    }))}
                    onSaveToJournal={phase === "done" ? handleSaveToJournal : undefined}
                  />
                )}

                {phase === "done" && (
                  <div className="flex justify-between items-center font-mono text-[10px] text-muted pt-1">
                    <span>
                      {traditionCards.length} sources &middot; grounded response
                    </span>
                    <span>was this grounded? &middot; &#128077; &middot; &#128078;</span>
                  </div>
                )}
              </div>
            </div>
          )}

          {phase === "error" && (
            <div className="flex gap-3.5">
              <div className="w-8 h-8 rounded-full border border-ink flex items-center justify-center font-serif text-sm flex-shrink-0">
                S
              </div>
              <div className="font-serif text-[17px] italic text-red-800">
                {error ?? "Something went wrong. Please try again."}
              </div>
            </div>
          )}
        </div>

        {showInput && (
          <div className="px-9 pb-6 pt-4 border-t border-line flex-shrink-0">
            <div className="max-w-[820px] mx-auto">
              {phase === "clarifying" ? (
                <Input
                  placeholder="Or type your own answer…"
                  value={reply}
                  onChange={setReply}
                  onSubmit={() => {
                    const trimmed = reply.trim();
                    if (trimmed) {
                      sendClarification(trimmed);
                      setReply("");
                    }
                  }}
                />
              ) : (
                <Input
                  placeholder="Ask a follow-up…"
                  value={reply}
                  onChange={setReply}
                />
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
