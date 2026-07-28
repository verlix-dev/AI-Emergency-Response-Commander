import { Activity, ArrowUpRight, Radio, ShieldAlert } from "lucide-react";

const milestones = [
  "Versioned API gateway",
  "PostgreSQL and migration foundation",
  "Commander workspace shell",
];

export default function HomePage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-6xl flex-col px-6 py-10 md:px-10">
      <header className="flex items-center justify-between border-b pb-6">
        <div className="flex items-center gap-3">
          <div className="rounded-lg bg-cyan-400/15 p-2 text-cyan-300"><ShieldAlert size={24} /></div>
          <div>
            <p className="text-lg font-semibold tracking-tight">Sentinel AI</p>
            <p className="text-xs text-muted-foreground">Emergency Response Decision Support</p>
          </div>
        </div>
        <span className="rounded-full border border-cyan-400/30 bg-cyan-400/10 px-3 py-1 text-xs font-medium text-cyan-200">MVP Foundation</span>
      </header>

      <section className="flex flex-1 flex-col justify-center py-16">
        <div className="max-w-3xl">
          <p className="mb-4 flex items-center gap-2 text-sm font-medium text-cyan-300"><Radio size={16} /> COMMAND PLATFORM INITIALIZING</p>
          <h1 className="text-4xl font-semibold tracking-tight md:text-6xl">A clear operating picture for emergency commanders.</h1>
          <p className="mt-6 max-w-2xl text-lg leading-8 text-muted-foreground">Sentinel AI will bring incident intelligence, resource readiness, and explainable response plans into a single commander workspace. It supports decisions; commanders remain in control.</p>
        </div>

        <div className="mt-12 grid gap-4 md:grid-cols-3">
          {milestones.map((item, index) => (
            <article key={item} className="rounded-xl border bg-card p-5">
              <span className="text-sm font-medium text-cyan-300">0{index + 1}</span>
              <p className="mt-6 font-medium">{item}</p>
              <ArrowUpRight className="mt-4 text-muted-foreground" size={18} />
            </article>
          ))}
        </div>
      </section>

      <footer className="flex items-center gap-2 border-t pt-6 text-sm text-muted-foreground"><Activity size={16} className="text-emerald-400" /> Platform base is online. Operational workflows are introduced in later milestones.</footer>
    </main>
  );
}
