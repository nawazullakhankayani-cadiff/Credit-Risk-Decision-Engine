import { useState } from "react";
import { Mail, MapPin, Clock, CheckCircle2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { Reveal } from "@/components/Reveal";

interface FormState {
  fullName: string;
  email: string;
  company: string;
  message: string;
}

interface FormErrors {
  fullName?: string;
  email?: string;
  message?: string;
}

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

const initialForm: FormState = {
  fullName: "",
  email: "",
  company: "",
  message: "",
};

export default function ContactSection() {
  const [form, setForm] = useState<FormState>(initialForm);
  const [errors, setErrors] = useState<FormErrors>({});
  const [submitted, setSubmitted] = useState<boolean>(false);

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
    setErrors((prev) => ({ ...prev, [name]: undefined }));
  };

  const validate = (values: FormState): FormErrors => {
    const next: FormErrors = {};
    if (!values.fullName.trim()) {
      next.fullName = "Please enter your full name.";
    }
    if (!values.email.trim()) {
      next.email = "Please enter your email address.";
    } else if (!EMAIL_REGEX.test(values.email.trim())) {
      next.email = "Please enter a valid email address.";
    }
    if (!values.message.trim()) {
      next.message = "Please tell us a bit about your needs.";
    } else if (values.message.trim().length < 10) {
      next.message = "Please add a little more detail (10+ characters).";
    }
    return next;
  };

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const nextErrors = validate(form);
    if (Object.keys(nextErrors).length > 0) {
      setErrors(nextErrors);
      return;
    }
    setErrors({});
    setSubmitted(true);
  };

  const handleReset = () => {
    setForm(initialForm);
    setErrors({});
    setSubmitted(false);
  };

  const firstName = form.fullName.trim().split(/\s+/)[0] || "there";

  const details = [
    { icon: Mail, label: "hello@creditcardrisk.ai" },
    { icon: MapPin, label: "Columbus, OH" },
    { icon: Clock, label: "Replies within one business day" },
  ];

  return (
    <section
      id="contact"
      className="scroll-mt-20 relative bg-background py-24 md:py-32"
    >
      <div className="mx-auto max-w-7xl px-8 lg:px-16">
        <Reveal>
          <div className="grid gap-12 lg:grid-cols-2">
            <div>
              <span className="text-xs font-semibold uppercase tracking-widest text-primary">
                GET A QUOTE
              </span>
              <h2 className="mt-4 text-3xl md:text-5xl font-bold tracking-tight text-foreground">
                Let&apos;s price your <span className="text-primary">risk</span>.
              </h2>
              <p className="mt-6 max-w-xl text-muted-foreground font-light">
                Tell us about your portfolio and where fraud, defaults, or
                chargebacks are hurting you most. Our risk team will map out how
                our models can tighten decisions and protect your margins.
              </p>

              <div className="mt-10 space-y-4">
                {details.map((item) => {
                  const Icon = item.icon;
                  return (
                    <div key={item.label} className="flex items-center gap-4">
                      <span className="inline-flex h-11 w-11 items-center justify-center rounded-lg bg-primary/10 text-primary">
                        <Icon className="h-5 w-5" />
                      </span>
                      <span className="text-foreground font-light">
                        {item.label}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="rounded-2xl border border-border bg-secondary/40 p-6 md:p-8">
              {submitted ? (
                <div className="flex flex-col items-start">
                  <span className="inline-flex h-14 w-14 items-center justify-center rounded-full bg-primary/10 text-primary">
                    <CheckCircle2 className="h-8 w-8" />
                  </span>
                  <h3 className="mt-6 text-2xl font-bold text-foreground">
                    Thanks, {firstName} — we&apos;ll be in touch.
                  </h3>
                  <p className="mt-2 text-muted-foreground font-light">
                    Our risk team replies within one business day.
                  </p>
                  <button
                    type="button"
                    onClick={handleReset}
                    className="mt-8 rounded-md px-4 py-2 text-sm font-medium text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
                  >
                    Send another
                  </button>
                </div>
              ) : (
                <form onSubmit={handleSubmit} noValidate className="space-y-5">
                  <div>
                    <label
                      htmlFor="fullName"
                      className="text-sm text-muted-foreground"
                    >
                      Full name
                    </label>
                    <input
                      id="fullName"
                      name="fullName"
                      type="text"
                      value={form.fullName}
                      onChange={handleChange}
                      placeholder="Jane Doe"
                      className={cn(
                        "mt-2 w-full rounded-md bg-muted border border-border px-4 py-3 text-foreground placeholder:text-muted-foreground/70 focus:outline-none focus:border-primary transition-colors",
                        errors.fullName && "border-destructive"
                      )}
                    />
                    {errors.fullName && (
                      <p className="mt-1 text-xs text-destructive">
                        {errors.fullName}
                      </p>
                    )}
                  </div>

                  <div>
                    <label
                      htmlFor="email"
                      className="text-sm text-muted-foreground"
                    >
                      Work email
                    </label>
                    <input
                      id="email"
                      name="email"
                      type="email"
                      value={form.email}
                      onChange={handleChange}
                      placeholder="jane@company.com"
                      className={cn(
                        "mt-2 w-full rounded-md bg-muted border border-border px-4 py-3 text-foreground placeholder:text-muted-foreground/70 focus:outline-none focus:border-primary transition-colors",
                        errors.email && "border-destructive"
                      )}
                    />
                    {errors.email && (
                      <p className="mt-1 text-xs text-destructive">
                        {errors.email}
                      </p>
                    )}
                  </div>

                  <div>
                    <label
                      htmlFor="company"
                      className="text-sm text-muted-foreground"
                    >
                      Company <span className="text-muted-foreground/60">(optional)</span>
                    </label>
                    <input
                      id="company"
                      name="company"
                      type="text"
                      value={form.company}
                      onChange={handleChange}
                      placeholder="Acme Financial"
                      className="mt-2 w-full rounded-md bg-muted border border-border px-4 py-3 text-foreground placeholder:text-muted-foreground/70 focus:outline-none focus:border-primary transition-colors"
                    />
                  </div>

                  <div>
                    <label
                      htmlFor="message"
                      className="text-sm text-muted-foreground"
                    >
                      How can we help?
                    </label>
                    <textarea
                      id="message"
                      name="message"
                      value={form.message}
                      onChange={handleChange}
                      rows={4}
                      placeholder="Tell us about your portfolio and the risk challenges you're facing…"
                      className={cn(
                        "mt-2 w-full rounded-md bg-muted border border-border px-4 py-3 text-foreground placeholder:text-muted-foreground/70 focus:outline-none focus:border-primary transition-colors resize-none",
                        errors.message && "border-destructive"
                      )}
                    />
                    {errors.message && (
                      <p className="mt-1 text-xs text-destructive">
                        {errors.message}
                      </p>
                    )}
                  </div>

                  <button
                    type="submit"
                    className="w-full bg-primary text-primary-foreground font-semibold rounded-md py-3 hover:brightness-110 active:scale-[0.98] transition"
                  >
                    Request my quote
                  </button>
                </form>
              )}
            </div>
          </div>
        </Reveal>
      </div>
    </section>
  );
}
