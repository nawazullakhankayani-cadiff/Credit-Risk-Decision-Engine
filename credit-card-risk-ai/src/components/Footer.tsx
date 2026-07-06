import { Twitter, Linkedin, Github } from "lucide-react";

const Footer = () => {
  return (
    <footer id="site-footer" className="scroll-mt-20 border-t border-border bg-hero-bg">
      <div className="mx-auto max-w-7xl px-8 lg:px-16 py-16">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
          <div className="col-span-2 md:col-span-1">
            <div className="text-lg font-semibold text-foreground">
              Credit Card Risk <span className="text-primary">AI</span>
            </div>
            <p className="mt-3 text-sm text-muted-foreground">
              AI-driven fraud detection, credit decisioning, and portfolio risk
              monitoring for card programs.
            </p>
            <div className="mt-5 flex items-center gap-4">
              <a
                href="#"
                aria-label="Twitter"
                className="text-muted-foreground hover:text-primary transition-colors"
              >
                <Twitter className="h-5 w-5" />
              </a>
              <a
                href="#"
                aria-label="LinkedIn"
                className="text-muted-foreground hover:text-primary transition-colors"
              >
                <Linkedin className="h-5 w-5" />
              </a>
              <a
                href="#"
                aria-label="GitHub"
                className="text-muted-foreground hover:text-primary transition-colors"
              >
                <Github className="h-5 w-5" />
              </a>
            </div>
          </div>

          <div>
            <h3 className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
              Product
            </h3>
            <nav className="mt-4">
              <a
                href="#platform"
                className="block py-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
              >
                Platform
              </a>
              <a
                href="#solutions"
                className="block py-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
              >
                Solutions
              </a>
              <a
                href="#customers"
                className="block py-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
              >
                Customers
              </a>
            </nav>
          </div>

          <div>
            <h3 className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
              Company
            </h3>
            <nav className="mt-4">
              <a
                href="#about-us"
                className="block py-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
              >
                About
              </a>
              <a
                href="#contact"
                className="block py-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
              >
                Contact
              </a>
            </nav>
          </div>

          <div>
            <h3 className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
              Resources
            </h3>
            <nav className="mt-4">
              <a
                href="#"
                className="block py-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
              >
                Docs
              </a>
              <a
                href="#"
                className="block py-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
              >
                API
              </a>
              <a
                href="#"
                className="block py-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
              >
                Security
              </a>
            </nav>
          </div>
        </div>

        <div className="mt-12 border-t border-border pt-6 flex flex-col md:flex-row items-center justify-between gap-4">
          <p className="text-sm text-muted-foreground">
            © 2026 Credit Card Risk AI. Columbus, OH.
          </p>
          <div className="flex items-center gap-6">
            <a
              href="#"
              className="text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              Privacy
            </a>
            <a
              href="#"
              className="text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              Terms
            </a>
          </div>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
