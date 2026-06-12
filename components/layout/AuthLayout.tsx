import { Wordmark, Squiggle } from "@/components/ui";

export function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen grid md:grid-cols-2 bg-paper text-ink">
      <div className="flex flex-col items-center justify-center gap-8 px-6 py-16">
        <Wordmark size={22} />
        <div className="w-full max-w-[400px]">{children}</div>
      </div>

      <div className="hidden md:flex flex-col items-center justify-center gap-7 bg-ink text-paper px-12 py-16">
        <div className="font-mono text-[11px] text-paper/60 uppercase tracking-widest">
          an ai wisdom companion
        </div>
        <div className="font-serif text-[34px] leading-[1.4] italic text-center max-w-[440px]">
          &ldquo;What is asking for your attention today?&rdquo;
        </div>
        <Squiggle width={104} className="text-paper/30" />
        <p className="text-[14px] text-paper/60 leading-[1.85] text-center max-w-[420px]">
          Soulra draws from Stoic, Vedanta, Buddhist, Sufi and other wisdom lineages —
          not to hand you a single answer, but to show you how each tradition sees your knot.
        </p>
      </div>
    </div>
  );
}
