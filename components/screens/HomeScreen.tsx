// components/screens/HomeScreen.tsx
import { Sidebar } from "@/components/layout";
import { Button } from "@/components/ui";
import { Chip } from "@/components/ui";
import { Input } from "@/components/ui";

export function HomeScreen() {
  return (
    <div className="flex h-screen bg-paper overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-auto">

        {/* greeting strip */}
        <div className="px-10 pt-8 pb-6 border-b border-line flex justify-between items-end">
          <div>
            <div className="font-mono text-[10px] text-muted uppercase tracking-widest">
              Friday · good morning
            </div>
            <div className="font-serif text-[36px] leading-tight mt-1.5">
              Welcome back, Mira.
            </div>
            <div className="text-sm text-muted mt-2 max-w-[580px] leading-relaxed">
              You've been working with the question of refusing well.
              Today's lesson is short. Then the day is yours.
            </div>
          </div>
          <Button small>◇ Open journal</Button>
        </div>

        {/* main grid */}
        <div className="px-10 py-6 grid grid-cols-[1.4fr_1fr] gap-5">

          {/* primary CTA */}
          <div className="col-span-2 border border-ink rounded-xl p-6 bg-paper-alt">
            <div className="font-mono text-[10px] text-accent uppercase tracking-widest mb-1.5">
              what is asking for your attention today?
            </div>
            <Input big />
            <div className="flex flex-wrap gap-1.5 mt-3.5 items-center">
              <span className="font-mono text-[10px] text-muted mr-1">or pick up a thread:</span>
              <Chip>refusing well · 4 days in</Chip>
              <Chip>holding loosely</Chip>
              <Chip>+ new thread</Chip>
            </div>
          </div>

          {/* today's teaching */}
          <div className="border border-ink rounded-xl bg-ink text-paper p-6">
            <div className="font-mono text-[10px] text-accent-soft uppercase tracking-widest mb-2">
              today's teaching · 2 min read
            </div>
            <div className="font-serif text-2xl leading-[1.35] italic">
              "You always own the option of having no opinion."
            </div>
            <div className="font-mono text-[10px] text-accent-soft mt-2.5">
              ↳ Marcus Aurelius · Meditations 6.13
            </div>
            <div className="text-sm text-[#cdc6b8] leading-[1.7] mt-3.5">
              Today's only practice: pause for one breath before answering the next request.
            </div>
            <div className="flex gap-2 mt-4">
              <button className="text-xs border border-accent-soft text-accent-soft rounded-full px-3 py-1.5">
                Sit with this →
              </button>
              <button className="text-xs border border-[#3a352d] text-accent-soft rounded-full px-3 py-1.5">
                ◇ Save
              </button>
            </div>
          </div>

          {/* revisit nudge */}
          <div className="border border-ink rounded-xl p-6 bg-paper">
            <div className="font-mono text-[10px] text-accent uppercase tracking-widest mb-2">
              a lesson you kept · 11 days ago
            </div>
            <div className="font-serif text-[19px] leading-[1.4] italic">
              "The yes that secures will resent itself."
            </div>
            <div className="font-mono text-[10px] text-muted mt-2">
              ↳ Bhagavad Gita 2.47
            </div>
            <div className="text-sm text-muted leading-[1.6] mt-3">
              Has it shown up in your week? Mark it lived, or set it down.
            </div>
            <div className="flex gap-2 mt-4">
              <Button small primary>It showed up</Button>
              <Button small>Not yet</Button>
            </div>
          </div>

          {/* recent threads */}
          <div className="col-span-2 border border-line rounded-xl p-5 bg-paper">
            <div className="flex justify-between items-center mb-3">
              <div className="font-mono text-[10px] text-muted uppercase tracking-widest">
                recent conversations
              </div>
              <span className="font-mono text-[10px] text-accent">see all ↗</span>
            </div>
            <div className="grid grid-cols-3 gap-3">
              {[
                ["Saying yes I don't mean", "2 days ago · 3 traditions", "career"],
                ["When grief just sits", "1 wk ago · Sufi · Buddhist", "grief"],
                ["Who am I without the role", "2 wk ago · Vedanta", "identity"],
              ].map(([title, meta, tag]) => (
                <div key={title} className="border border-line rounded-lg p-3 bg-paper-alt">
                  <div className="font-serif text-[15px] leading-[1.35] italic">"{title}"</div>
                  <div className="flex justify-between items-center mt-2.5">
                    <span className="font-mono text-[9px] text-muted">{meta}</span>
                    <Chip className="text-[9px] px-2 py-0.5">{tag}</Chip>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
