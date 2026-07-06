# Credit Card Risk AI — Hero Landing Page

A full-screen dark hero landing page with an embedded **Spline 3D** background, built
with **React + Vite + TypeScript + Tailwind CSS + shadcn/ui**.

## Stack

- React 18 + Vite + TypeScript
- Tailwind CSS (dark-only theme, HSL CSS variables) + `tailwindcss-animate`
- shadcn/ui `Button` with custom `navCta` / `hero` / `heroOutline` variants (via `class-variance-authority`)
- `@splinetool/react-spline` + `@splinetool/runtime` for the 3D scene
- Google Font **Sora** (300–700)

## Getting started

```bash
cd credit-card-risk-ai
npm install
npm run dev      # http://localhost:5173
```

Build for production:

```bash
npm run build
npm run preview
```

## Structure

```
index.html                  # loads Sora font, mounts #root
src/
  main.tsx                  # React entry
  App.tsx                   # renders <Index />
  index.css                 # Tailwind layers + theme CSS variables
  pages/Index.tsx           # page wrapper: <Navbar /> + <HeroSection />
  components/
    Navbar.tsx              # fixed transparent nav floating over the scene
    HeroSection.tsx         # full-screen hero, lazy Spline background, bottom-left content
    ui/button.tsx           # shadcn Button + custom variants
  lib/utils.ts              # cn() helper
tailwind.config.ts          # theme tokens, fade-up / fade-in keyframes
```

## Notes

- The Spline scene (`https://prod.spline.design/Slk6b8kz3LRlKiyk/scene.splinecode`) is
  lazy-loaded inside a `<Suspense>` with a solid `hero-bg` fallback, so the page paints
  instantly while the 3D scene streams in.
- The hero content area is `pointer-events-none` so cursor/drag interactions reach the
  Spline canvas; the two CTA buttons re-enable clicks with `pointer-events-auto`.
- Dark theme only — the `dark` class is set on `<html>` and there is no light mode.
