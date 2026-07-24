# Building an artifact

This is the contract for creating a web artifact for this platform — written so
an LLM (or a human) can produce one that drops straight in and looks native.
Read it fully before writing any HTML.

## Where it goes

One folder per artifact under `artifacts/`:

```
artifacts/<slug>/
├── index.html     # required — the artifact itself
├── meta.json      # optional — { "title": "...", "description": "..." }
└── ...            # any other static assets (images, data, css)
```

- `<slug>` is lowercase letters, digits, and inner hyphens (`gear-calculator`).
- `meta.json` sets how the artifact appears on the device's index page and in
  cross-device discovery. If it's missing or a field is absent, the slug is used
  as the title and the description is blank. Always include it.
- Scaffold the folder with `scripts/new-artifact.sh <slug> "Title" "Description"`,
  then replace the placeholder `index.html` with a copy of the closest template.

## Hard rules (non-negotiable)

1. **Fully self-contained.** One `index.html` with inline `<style>` and `<script>`.
   **No external requests** — no CDN scripts, no Google Fonts, no remote images.
   Artifacts are served as static files behind Tailscale Funnel; anything that
   reaches out to another host will fail or leak. Embed assets as `data:` URIs.
   (Same-origin `fetch` to your own artifact's files is fine.)
2. **Use the UQR design tokens** below, verbatim, in a `:root` block. This is
   what keeps every artifact looking like one system.
3. **Responsive.** Relative units, `max-width` on containers, wraps on narrow
   screens. Never force horizontal body scroll.
4. **Dark, always.** The UQR brand is dark. Do not add a light mode.
5. **No secrets, no personal data** baked into the file — it's public via Funnel.

## The design tokens

Paste this `:root` block into every artifact's `<style>` and build from the
variables (never hard-code the hexes elsewhere):

```css
:root{
  color-scheme:dark;
  --bg:#201b26;                      /* page background            */
  --surface:rgba(255,255,255,.024);  /* card fill                  */
  --surface-2:rgba(255,255,255,.04); /* inset / icon box           */
  --line:rgba(255,255,255,.12);      /* hairline borders           */
  --ink:#fff;                        /* primary text               */
  --muted:rgba(255,255,255,.6);      /* secondary text             */
  --accent:#d7df23;                  /* signature lime-yellow       */
  --purple:#5c13aa;                  /* primary action             */
  --purple-deep:#3b1f70;             /* deep purple                */
  --radius:16px; --pill:9999px;
  --shadow:0 18px 44px rgba(0,0,0,.3);
  --font:"Helvetica Neue",Helvetica,Arial,"Inter",system-ui,sans-serif;
}
```

The brand font is **Akzidenz-Grotesk** (licensed, so not loaded here — the stack
above is the closest system fallback). If you have a licensed webfont file,
embed it with `@font-face` using a `data:` URI and prepend it to `--font`.

## House style — use these, don't reinvent

- **Accent, sparingly.** One emphasis word per heading in `var(--accent)`
  (`<span class="accent">`). It's a highlight, not a body color.
- **Buttons are pills.** `border-radius:var(--pill)`, primary = `var(--purple)`
  fill + white bold text; secondary = `var(--surface-2)` fill + `var(--line)`
  border.
- **Cards/tiles** = `16px` radius, a faint top-down white gradient over
  `var(--surface)`, a `1px var(--line)` border, and `var(--shadow)`.
- **Dashboard stat tiles**: a 64px rounded icon box (`var(--surface-2)` fill,
  inline SVG stroked in `var(--accent)`), a big bold `tabular-nums` value, and a
  `var(--muted)` label — see the dashboard template.
- **Numbers** use `font-variant-numeric:tabular-nums` so they don't jitter.

## Which template to start from

Copy the closest one from `templates/` and edit only the marked `TODO` spots:

| Artifact is…                                   | Start from            |
|------------------------------------------------|-----------------------|
| one interactive widget (input → action → result) | `templates/tool/`     |
| live metrics / a grid of stat tiles            | `templates/dashboard/`|
| an article, report, or changelog               | `templates/document/` |

Each template is a complete, working page. The `tool` and `dashboard` templates
isolate their logic in a single function (`compute()` / `fetchMetrics()`) —
replace that and the tile/field definitions, leave the styling alone.

## meta.json

```json
{
  "title": "Gear Ratio Calculator",
  "description": "Work out final drive from sprocket teeth."
}
```

`title` and `description` are what other devices on the tailnet show when they
link to this artifact, so write them for a stranger skimming a list.
