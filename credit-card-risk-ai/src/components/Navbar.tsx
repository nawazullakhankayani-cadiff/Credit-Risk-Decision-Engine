import { useEffect, useState } from "react";
import { Menu, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const navLinks = ["Platform", "Solutions", "Customers", "About Us", "Contact"];

const toId = (label: string) => label.toLowerCase().replace(/\s+/g, "-");

const scrollToId = (id: string) => {
  document.getElementById(id)?.scrollIntoView({ behavior: "smooth" });
};

const Navbar = () => {
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);

  // Add a solid backdrop once the user scrolls past the hero, for legibility.
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 40);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  // Lock body scroll while the mobile menu is open.
  useEffect(() => {
    document.body.style.overflow = open ? "hidden" : "";
    return () => {
      document.body.style.overflow = "";
    };
  }, [open]);

  return (
    <header
      className={cn(
        "fixed top-0 left-0 right-0 z-50 transition-colors duration-300",
        scrolled || open
          ? "bg-hero-bg/85 backdrop-blur-md border-b border-border"
          : "bg-transparent"
      )}
    >
      <div className="flex items-center justify-between px-8 lg:px-16 py-5">
        {/* Left: Logo */}
        <a
          href="#"
          onClick={(e) => {
            e.preventDefault();
            setOpen(false);
            window.scrollTo({ top: 0, behavior: "smooth" });
          }}
          className="text-foreground text-xl font-semibold tracking-tight"
        >
          Credit Card Risk <span className="text-primary">AI</span>
        </a>

        {/* Center: Nav links (desktop) */}
        <nav className="hidden md:flex items-center gap-8">
          {navLinks.map((link) => (
            <a
              key={link}
              href={`#${toId(link)}`}
              className="text-sm text-muted-foreground hover:text-foreground transition-colors uppercase tracking-widest"
            >
              {link}
            </a>
          ))}
        </nav>

        {/* Right: CTA (desktop) */}
        <Button
          variant="navCta"
          size="lg"
          onClick={() => scrollToId("contact")}
          className="hidden md:inline-flex rounded-lg uppercase text-xs tracking-widest px-6"
        >
          Get Quote
        </Button>

        {/* Mobile: menu toggle */}
        <button
          type="button"
          aria-label={open ? "Close menu" : "Open menu"}
          aria-expanded={open}
          onClick={() => setOpen((v) => !v)}
          className="md:hidden inline-flex h-10 w-10 items-center justify-center rounded-lg bg-nav-button text-foreground active:scale-95 transition-transform"
        >
          {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </div>

      {/* Mobile menu overlay */}
      <div
        className={cn(
          "md:hidden overflow-hidden bg-hero-bg/95 backdrop-blur-md transition-[max-height,opacity] duration-300 ease-out",
          open ? "max-h-[80vh] opacity-100 border-t border-border" : "max-h-0 opacity-0"
        )}
      >
        <nav className="flex flex-col px-8 py-6 gap-1">
          {navLinks.map((link) => (
            <a
              key={link}
              href={`#${toId(link)}`}
              onClick={(e) => {
                e.preventDefault();
                setOpen(false);
                document.body.style.overflow = "";
                // Wait for the menu to collapse before scrolling so the
                // native anchor jump isn't cancelled by the layout change.
                requestAnimationFrame(() => scrollToId(toId(link)));
              }}
              className="py-3 text-sm text-muted-foreground hover:text-foreground transition-colors uppercase tracking-widest border-b border-border/60"
            >
              {link}
            </a>
          ))}
          <Button
            variant="hero"
            onClick={() => {
              setOpen(false);
              scrollToId("contact");
            }}
            className="mt-4 w-full rounded-lg uppercase text-xs tracking-widest"
          >
            Get Quote
          </Button>
        </nav>
      </div>
    </header>
  );
};

export default Navbar;
