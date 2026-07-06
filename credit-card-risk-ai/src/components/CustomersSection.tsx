import { Quote } from "lucide-react";
import { Reveal } from "@/components/Reveal";

type Stat = {
  value: string;
  label: string;
};

type Testimonial = {
  quote: string;
  name: string;
  role: string;
  initials: string;
};

const stats: Stat[] = [
  { value: "12M+", label: "transactions scored" },
  { value: "$48M+", label: "fraud prevented" },
  { value: "0.795", label: "model AUC" },
  { value: "<50ms", label: "decision latency" },
];

const testimonials: Testimonial[] = [
  {
    quote:
      "We cut fraud losses by 41% in the first quarter and our analysts finally trust the scores.",
    name: "Dana Holt",
    role: "Head of Risk, Meridian Capital",
    initials: "DH",
  },
  {
    quote:
      "Calibrated PD meant we could approve thin-file customers we used to auto-decline.",
    name: "Renee Okafor",
    role: "VP Lending, Pinnacle BNPL",
    initials: "RO",
  },
  {
    quote:
      "Chargebacks dropped and disputes are basically self-documenting now.",
    name: "Marcus Lee",
    role: "Payments Lead, Northwind Finance",
    initials: "ML",
  },
];

const wordmarks: string[] = [
  "Northwind Finance",
  "Acme Card",
  "Sterling CU",
  "Meridian Capital",
  "BluePeak",
  "Pinnacle BNPL",
];

export default function CustomersSection() {
  return (
    <section
      id="customers"
      className="scroll-mt-20 relative bg-background py-24 md:py-32"
    >
      <div className="mx-auto max-w-7xl px-8 lg:px-16">
        <Reveal className="max-w-2xl">
          <span className="text-xs font-semibold uppercase tracking-widest text-primary">
            CUSTOMERS
          </span>
          <h2 className="mt-4 text-3xl md:text-5xl font-bold tracking-tight text-foreground leading-tight">
            Trusted where the <span className="text-primary">money moves.</span>
          </h2>
        </Reveal>

        <Reveal delay={100}>
          <div className="mt-14 grid grid-cols-2 md:grid-cols-4 gap-8">
            {stats.map((stat) => (
              <div key={stat.label}>
                <div className="text-3xl md:text-4xl font-bold text-primary">
                  {stat.value}
                </div>
                <div className="mt-2 text-sm text-muted-foreground">
                  {stat.label}
                </div>
              </div>
            ))}
          </div>
        </Reveal>

        <Reveal delay={150}>
          <div className="mt-16 grid grid-cols-1 md:grid-cols-3 gap-6">
            {testimonials.map((t) => (
              <div
                key={t.name}
                className="flex flex-col rounded-xl border border-border bg-secondary/40 p-6 hover:border-primary/40 hover:bg-secondary/60 transition-colors"
              >
                <Quote className="h-5 w-5 text-primary/80" />
                <p className="mt-4 flex-1 text-foreground/90 font-light">
                  &ldquo;{t.quote}&rdquo;
                </p>
                <div className="mt-6 flex items-center gap-3">
                  <span className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-primary/15 text-sm font-semibold text-primary">
                    {t.initials}
                  </span>
                  <div>
                    <div className="font-semibold text-foreground">{t.name}</div>
                    <div className="text-sm text-muted-foreground">{t.role}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Reveal>

        <Reveal delay={200}>
          <div className="mt-16 flex flex-wrap items-center justify-center gap-x-10 gap-y-4">
            {wordmarks.map((name) => (
              <span
                key={name}
                className="text-muted-foreground/60 font-semibold"
              >
                {name}
              </span>
            ))}
          </div>
        </Reveal>
      </div>
    </section>
  );
}
