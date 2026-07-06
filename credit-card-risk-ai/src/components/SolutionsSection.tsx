import { CreditCard, Wallet, Store, Boxes, Check } from "lucide-react";
import { Reveal } from "@/components/Reveal";

type Solution = {
  icon: typeof CreditCard;
  segment: string;
  promise: string;
  items: string[];
};

const solutions: Solution[] = [
  {
    icon: CreditCard,
    segment: "Card issuers",
    promise: "Approve more good customers, decline fraud.",
    items: [
      "Real-time authorization scoring",
      "Credit-line decisioning",
      "Adverse-action reason codes",
    ],
  },
  {
    icon: Wallet,
    segment: "BNPL & lending",
    promise: "Underwrite thin-file borrowers with confidence.",
    items: [
      "Calibrated probability of default",
      "Affordability checks",
      "Instant approve/refer/decline",
    ],
  },
  {
    icon: Store,
    segment: "Merchants & acquirers",
    promise: "Cut chargebacks without losing sales.",
    items: [
      "Pre-auth risk scoring",
      "Dispute prevention",
      "Smart 3DS step-up routing",
    ],
  },
  {
    icon: Boxes,
    segment: "Fintechs & platforms",
    promise: "Ship risk infrastructure, not a team.",
    items: [
      "API-first integration",
      "Full sandbox",
      "SOC 2-ready controls",
    ],
  },
];

export default function SolutionsSection() {
  return (
    <section id="solutions" className="scroll-mt-20 relative bg-hero-bg py-24 md:py-32">
      <div className="mx-auto max-w-7xl px-8 lg:px-16">
        <Reveal>
          <div className="max-w-2xl">
            <span className="text-xs font-semibold uppercase tracking-widest text-primary">
              SOLUTIONS
            </span>
            <h2 className="mt-4 text-3xl md:text-5xl font-bold tracking-tight text-foreground leading-tight">
              Built for every team that touches a{" "}
              <span className="text-primary">card.</span>
            </h2>
            <p className="mt-6 text-muted-foreground font-light">
              One risk engine, tuned to the decisions your team makes every day —
              from the first authorization to the last dispute.
            </p>
          </div>

          <div className="mt-14 grid grid-cols-1 md:grid-cols-2 gap-6">
            {solutions.map((solution) => {
              const Icon = solution.icon;
              return (
                <div
                  key={solution.segment}
                  className="rounded-xl border border-border bg-secondary/40 p-6 hover:border-primary/40 hover:bg-secondary/60 transition-colors"
                >
                  <div className="flex items-start gap-4">
                    <span className="inline-flex h-11 w-11 items-center justify-center rounded-lg bg-primary/10 text-primary shrink-0">
                      <Icon className="h-5 w-5" />
                    </span>
                    <div>
                      <h3 className="font-semibold text-foreground">
                        {solution.segment}
                      </h3>
                      <p className="mt-1 text-muted-foreground font-light">
                        {solution.promise}
                      </p>
                    </div>
                  </div>

                  <ul className="mt-6 space-y-3">
                    {solution.items.map((item) => (
                      <li key={item} className="flex items-center gap-3">
                        <Check className="h-4 w-4 text-primary shrink-0" />
                        <span className="text-sm text-muted-foreground">
                          {item}
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              );
            })}
          </div>
        </Reveal>
      </div>
    </section>
  );
}
