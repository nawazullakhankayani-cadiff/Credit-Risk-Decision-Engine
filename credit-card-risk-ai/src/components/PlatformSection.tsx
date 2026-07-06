import {
  ShieldCheck,
  Gauge,
  FileSearch,
  ShieldAlert,
  LineChart,
  Webhook,
} from "lucide-react";
import { Reveal } from "@/components/Reveal";

type Feature = {
  icon: typeof ShieldCheck;
  title: string;
  description: string;
};

const features: Feature[] = [
  {
    icon: ShieldCheck,
    title: "Real-time fraud detection",
    description:
      "Score every transaction in under 50ms and block risky ones before they clear.",
  },
  {
    icon: Gauge,
    title: "Calibrated credit decisioning",
    description:
      "Probability of default with isotonic calibration; approve, refer, or decline automatically.",
  },
  {
    icon: FileSearch,
    title: "Explainable reason codes",
    description:
      "Every decision ships with ranked, human-readable drivers for adverse-action notices.",
  },
  {
    icon: ShieldAlert,
    title: "Chargeback & dispute shield",
    description:
      "Flag likely disputes early and auto-assemble evidence packets.",
  },
  {
    icon: LineChart,
    title: "Portfolio monitoring",
    description:
      "Track approval rate, loss rate and PSI drift with alerts before performance slips.",
  },
  {
    icon: Webhook,
    title: "Drop-in API & webhooks",
    description: "REST + webhooks and SDKs; go live in days, not quarters.",
  },
];

export default function PlatformSection() {
  return (
    <section
      id="platform"
      className="scroll-mt-20 relative bg-background py-24 md:py-32"
    >
      <div className="mx-auto max-w-7xl px-8 lg:px-16">
        <Reveal className="max-w-2xl">
          <span className="text-xs font-semibold uppercase tracking-widest text-primary">
            THE PLATFORM
          </span>
          <h2 className="mt-4 text-3xl md:text-5xl font-bold tracking-tight text-foreground">
            Everything you need to stop fraud and price{" "}
            <span className="text-primary">risk</span>.
          </h2>
          <p className="mt-6 text-muted-foreground font-light">
            One decisioning layer for fraud, credit and disputes — calibrated,
            explainable and production-ready from day one.
          </p>
        </Reveal>

        <Reveal delay={100}>
          <div className="mt-14 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {features.map((feature) => {
              const Icon = feature.icon;
              return (
                <div
                  key={feature.title}
                  className="rounded-xl border border-border bg-secondary/40 p-6 hover:border-primary/40 hover:bg-secondary/60 transition-colors"
                >
                  <span className="inline-flex h-11 w-11 items-center justify-center rounded-lg bg-primary/10 text-primary">
                    <Icon className="h-5 w-5" />
                  </span>
                  <h3 className="mt-5 text-foreground font-semibold">
                    {feature.title}
                  </h3>
                  <p className="mt-2 text-muted-foreground text-sm">
                    {feature.description}
                  </p>
                </div>
              );
            })}
          </div>
        </Reveal>
      </div>
    </section>
  );
}
