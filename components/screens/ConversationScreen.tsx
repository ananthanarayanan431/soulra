"use client";
import { useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { Sidebar } from "@/components/layout";
import { Button, Input } from "@/components/ui";
import { TraditionCard } from "@/components/conversation/TraditionCard";
import { ActionPlan } from "@/components/conversation/ActionPlan";
import { ClarifyingPause } from "@/components/conversation/ClarifyingPause";
import { useSoulraChat } from "@/hooks/useSoulraChat";

const STATUS_LABELS: Record<string, string> = {
  intake:          "Understanding your situation…",
  retrieve:        "Searching wisdom traditions…",
  rerank:          "Refining passages…",
  grade_docs:      "Evaluating relevance…",
  rewrite_query:   "Deepening the search…",
  clarify:         "Preparing a question…",
  retrieve_refined: "Searching further…",
  rerank_refined:  "Refining results…",
  synthesize:      "Drawing from the traditions…",
};

function ThinkingIndicator({ node }: { node: string }) {
  return (
    <div className="flex gap-3.5">
      <div className="w-8 h-8 rounded-full border border-ink flex items-center justify-center font-serif text-sm flex-shrink-0">
        S
      </div>
      <div className="flex-1 pt-1">
        <div className="font-mono text-[10px] text-muted uppercase tracking-wide mb-1.5">
          Soulra
        </div>
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

export function ConversationScreen() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const situation = searchParams.get("q") ?? "";

  const [reply, setReply] = useState("");

  const { state, sendClarification } = useSoulraChat(situation);
  const {
    phase,
    statusNode,
    clarifyQuestion,
    clarifyOptions,
    clarifyAnswer,
    traditionCards,
    actionSteps,
    error,
  } = state;

  // No situation — show entry input
  if (!situation) {
    return (
      <div className="flex h-screen bg-paper overflow-hidden">
        <Sidebar />
        <div className="flex-1 flex flex-col items-center justify-center gap-6 px-10">
          <div className="font-serif text-[32px] leading-[1.3] text-center max-w-[500px]">
            What is asking for your attention today?
          </div>
          <div className="w-full max-w-[580px]">
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

          {/* user situation bubble */}
          <UserBubble text={situation} />

          {/* thinking */}
          {(phase === "connecting" || phase === "thinking") && (
            <ThinkingIndicator node={statusNode} />
          )}

          {/* clarifying pause */}
          {clarifyQuestion && (
            <ClarifyingPause
              question={clarifyQuestion}
              options={clarifyOptions}
              onSelect={isActive ? sendClarification : undefined}
            />
          )}

          {/* user's clarify answer */}
          {clarifyAnswer && <UserBubble text={clarifyAnswer} />}

          {/* responding indicator */}
          {phase === "responding" && <ThinkingIndicator node={statusNode} />}

          {/* tradition cards + action plan */}
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

          {/* error */}
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

        {/* input bar */}
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
