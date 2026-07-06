import { lazy, Suspense } from "react";

// Lazy-load the Spline runtime so the page shell paints immediately and the
// heavy 3D scene streams in behind it.
const Spline = lazy(() => import("@splinetool/react-spline"));

const HeroSection = () => {
  return (
    <section className="relative min-h-screen flex items-end bg-hero-bg overflow-hidden">
      {/* Spline 3D background */}
      <div className="absolute inset-0">
        <Suspense fallback={<div className="absolute inset-0 bg-hero-bg" />}>
          <Spline
            scene="https://prod.spline.design/Slk6b8kz3LRlKiyk/scene.splinecode"
            className="w-full h-full"
          />
        </Suspense>
      </div>

      {/* Dark overlay for contrast */}
      <div className="absolute inset-0 bg-black/30 z-[1] pointer-events-none" />

      {/* Content — anchored bottom-left, clicks pass through to the scene */}
      <div className="relative z-10 pointer-events-none w-full max-w-[90%] sm:max-w-md lg:max-w-2xl px-6 md:px-10 pb-10 md:pb-10 pt-32">
        <h1
          className="opacity-0 animate-fade-up text-[clamp(3rem,8vw,6rem)] font-bold leading-[1.05] tracking-[-0.05em] text-foreground mb-2 md:mb-4 uppercase"
          style={{ animationDelay: "0.2s" }}
        >
          Credit Card Risk <span className="text-primary">AI</span>
        </h1>

        <p
          className="opacity-0 animate-fade-up text-foreground/80 text-[clamp(1.125rem,2.5vw,1.875rem)] font-light mb-3 md:mb-6"
          style={{ animationDelay: "0.4s" }}
        >
          We score credit risk correctly.
        </p>

        <p
          className="opacity-0 animate-fade-up text-muted-foreground text-[clamp(0.875rem,1.5vw,1.25rem)] font-light mb-4 md:mb-8"
          style={{ animationDelay: "0.55s" }}
        >
          Real-time fraud detection that flags risky transactions before they
          clear. AI-driven credit decisioning with calibrated probability of
          default and clear reason codes. Chargeback and dispute prevention
          across your entire card portfolio. All of it accurate and audit-ready,
          not just fast.
        </p>

        <div
          className="opacity-0 animate-fade-up flex flex-wrap gap-3 font-bold"
          style={{ animationDelay: "0.7s" }}
        >
          <button
            onClick={() =>
              document
                .getElementById("contact")
                ?.scrollIntoView({ behavior: "smooth" })
            }
            className="pointer-events-auto bg-primary text-primary-foreground px-6 py-3 md:px-8 md:py-4 text-sm rounded-sm cursor-pointer hover:brightness-110 transition-all active:scale-[0.97]"
          >
            Book a Call
          </button>
          <button
            onClick={() =>
              document
                .getElementById("customers")
                ?.scrollIntoView({ behavior: "smooth" })
            }
            className="pointer-events-auto bg-white text-background px-6 py-3 md:px-8 md:py-4 text-sm rounded-sm cursor-pointer hover:brightness-90 transition-all active:scale-[0.97]"
          >
            Our Work
          </button>
        </div>

        <p
          className="opacity-0 animate-fade-up text-muted-foreground/60 text-xs font-light mt-4 md:mt-6"
          style={{ animationDelay: "0.85s" }}
        >
          Trusted credit-risk partner. Columbus, OH. 12M+ transactions scored.
        </p>
      </div>
    </section>
  );
};

export default HeroSection;
