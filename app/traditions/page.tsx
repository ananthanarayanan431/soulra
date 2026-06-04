import { Sidebar } from "@/components/layout";
import { Chip } from "@/components/ui";

const TRADITIONS = [
  { name: "Vedanta",           origin: "India · ~800 BCE",          era: "ancient",   sources: 87,  passages: 4200, picked: true  },
  { name: "Buddhism",           origin: "India / E. Asia · ~500 BCE", era: "ancient",   sources: 94,  passages: 5100, picked: true  },
  { name: "Taoism",             origin: "China · ~600 BCE",           era: "ancient",   sources: 48,  passages: 1820, picked: false },
  { name: "Stoicism",           origin: "Greece · ~300 BCE",          era: "ancient",   sources: 62,  passages: 3400, picked: true  },
  { name: "Jewish wisdom",      origin: "Levant · ~500 BCE",          era: "ancient",   sources: 39,  passages: 2600, picked: false },
  { name: "Christian mystics",  origin: "Europe · ~1200 CE",          era: "medieval",  sources: 44,  passages: 2900, picked: false },
  { name: "Sufism",             origin: "Persia · ~900 CE",           era: "medieval",  sources: 31,  passages: 1600, picked: false },
  { name: "Zen",                origin: "Japan · ~1200 CE",           era: "medieval",  sources: 29,  passages: 1400, picked: false },
  { name: "Indigenous & earth", origin: "Many lineages",             era: "perennial", sources: 18,  passages: 880,  picked: false },
];

export default function TraditionsPage() {
  return (
    <div className="flex h-screen bg-paper overflow-hidden">
      <Sidebar />

      <div className="flex-1 flex flex-col overflow-hidden">
        {/* header */}
        <div className="px-10 pt-7 pb-5 border-b border-line flex-shrink-0">
          <div className="font-mono text-[10px] text-muted uppercase tracking-widest">
            wisdom traditions
          </div>
          <div className="font-serif text-[36px] leading-tight mt-1">
            The voices in your room
          </div>
          <div className="text-[13px] text-muted mt-2 max-w-[540px] leading-relaxed">
            Soulra draws from these lineages when answering your questions. Pick three or more to
            keep in the room — you can always change them.
          </div>
        </div>

        {/* body */}
        <div className="flex-1 overflow-auto px-10 py-7">
          {/* active selection summary */}
          <div className="border-[1.5px] border-ink rounded-xl p-5 bg-paper-alt mb-7 flex items-start justify-between gap-6">
            <div className="flex-1">
              <div className="font-mono text-[10px] text-muted uppercase tracking-widest mb-3">
                your selection · {TRADITIONS.filter(t => t.picked).length} of {TRADITIONS.length} voices
              </div>
              <div className="flex flex-wrap gap-2">
                {TRADITIONS.filter(t => t.picked).map(t => (
                  <span
                    key={t.name}
                    className="text-[11px] px-2.5 py-1 rounded-full bg-ink text-paper"
                  >
                    {t.name} ×
                  </span>
                ))}
              </div>
            </div>
            <div className="font-mono text-[10px] text-muted leading-relaxed text-right flex-shrink-0">
              412 source texts<br />26,400 passages indexed
            </div>
          </div>

          {/* era filters */}
          <div className="flex gap-2 mb-6">
            <span className="font-mono text-[10px] text-muted self-center mr-1">filter:</span>
            {["all", "ancient", "medieval", "perennial"].map(era => (
              <Chip key={era} active={era === "all"}>
                {era}
              </Chip>
            ))}
          </div>

          {/* tradition cards grid */}
          <div className="grid grid-cols-3 gap-3">
            {TRADITIONS.map(t => (
              <div
                key={t.name}
                className={`rounded-xl p-5 cursor-pointer transition-all ${
                  t.picked
                    ? "border-[1.5px] border-ink bg-ink text-paper shadow-md"
                    : "border border-line bg-paper hover:border-ink"
                }`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className={`font-serif text-[18px] font-medium ${t.picked ? "text-paper" : "text-ink"}`}>
                      {t.name}
                    </div>
                    <div className={`font-mono text-[9px] mt-1 tracking-wide ${t.picked ? "text-accent-soft" : "text-muted"}`}>
                      {t.origin}
                    </div>
                  </div>
                  <span className={`font-mono text-[13px] flex-shrink-0 mt-0.5 ${t.picked ? "text-accent-soft" : "text-muted"}`}>
                    {t.picked ? "✓" : "+"}
                  </span>
                </div>
                <div className={`font-mono text-[10px] mt-3 pt-3 border-t ${t.picked ? "border-[#3a352d] text-accent-soft" : "border-dashed border-line text-muted"}`}>
                  {t.sources} sources &middot; {t.passages.toLocaleString()} passages
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
