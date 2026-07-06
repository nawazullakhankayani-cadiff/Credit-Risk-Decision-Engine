import { FileCheck, Scale, Users } from "lucide-react";
import { Reveal } from "@/components/Reveal";

const values = [
  {
    icon: FileCheck,
    title: "Explainable by default",
    description: "Reason codes and audit trails on every score.",
  },
  {
    icon: Scale,
    title: "Calibrated, not just accurate",
    description: "Stated probabilities match observed outcomes.",
  },
  {
    icon: Users,
    title: "Human-in-the-loop",
    description: "Borderline cases route to analysts, never auto-decided in silence.",
  },
];

export default function AboutSection() {
  return (
    <section id="about-us" className="scroll-mt-20 relative bg-hero-bg py-24 md:py-32">
      <div className="mx-auto max-w-7xl px-8 lg:px-16">
        <div className="grid items-center gap-12 lg:grid-cols-2">
          <Reveal>
            <div>
              <span className="text-xs font-semibold uppercase tracking-widest text-primary">
                About Us
              </span>
              <h2 className="mt-4 text-3xl md:text-5xl font-bold tracking-tight text-foreground leading-tight">
                We build risk systems that hold up in an{" "}
                <span className="text-primary">audit</span>.
              </h2>
              <p className="mt-6 max-w-2xl text-muted-foreground font-light">
                Founded by risk and ML engineers in Columbus, Ohio, Credit Card
                Risk AI pairs calibrated models with explainability and
                human-in-the-loop review so that every decision is defensible —
                to a regulator, an auditor, or the customer it affects.
              </p>
              <p className="mt-4 max-w-2xl text-muted-foreground font-light">
                We treat transparency as a feature, not an afterthought. This
                site is illustrative portfolio context and does not represent a
                live production deployment or real cardholder data.
              </p>
            </div>
          </Reveal>

          <Reveal delay={150}>
            <div className="grid grid-cols-1 gap-5">
              {values.map((value) => {
                const Icon = value.icon;
                return (
                  <div
                    key={value.title}
                    className="flex items-start gap-4 rounded-xl border border-border bg-secondary/40 p-6 transition-colors hover:border-primary/40 hover:bg-secondary/60"
                  >
                    <span className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                      <Icon className="h-5 w-5" />
                    </span>
                    <div>
                      <h3 className="text-lg font-semibold text-foreground">
                        {value.title}
                      </h3>
                      <p className="mt-1 text-sm text-muted-foreground font-light">
                        {value.description}
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>
          </Reveal>
        </div>
      </div>
    </section>
  );
}
