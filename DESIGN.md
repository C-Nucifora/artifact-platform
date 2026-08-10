---
name: Artifact Platform
description: A dark technical control plane for a self-forming artifact mesh.
colors:
  void-canvas: "#090d12"
  deep-canvas: "#05080b"
  instrument-panel: "#101820"
  raised-panel: "#15212b"
  soft-panel: "#0d141b"
  structural-line: "#2c3a46"
  strong-line: "#52616c"
  primary-ink: "#f1f5f3"
  secondary-ink: "#b5c0c8"
  telemetry-ink: "#84919a"
  mesh-signal: "#b9ed70"
  signal-depth: "#18280f"
  peer-cobalt: "#6ea0ff"
  warning-amber: "#f0be6b"
  fault-red: "#ff7b72"
typography:
  display:
    fontFamily: "Barlow Semi Condensed, Arial Narrow, sans-serif"
    fontSize: "clamp(4rem, 9vw, 6rem)"
    fontWeight: 800
    lineHeight: 0.8
    letterSpacing: "-0.025em"
  body:
    fontFamily: "Avenir Next, Avenir, Segoe UI, Helvetica, Arial, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "SFMono-Regular, Consolas, Liberation Mono, monospace"
    fontSize: "0.68rem"
    fontWeight: 700
    lineHeight: 1.3
    letterSpacing: "0.05em"
rounded:
  square: "0"
  indicator: "50%"
spacing:
  xs: "0.45rem"
  sm: "0.75rem"
  md: "1rem"
  lg: "1.5rem"
  xl: "2rem"
  section: "clamp(4.5rem, 8vw, 8rem)"
components:
  button-primary:
    backgroundColor: "{colors.mesh-signal}"
    textColor: "{colors.deep-canvas}"
    typography: "{typography.label}"
    rounded: "{rounded.square}"
    padding: "0.7rem 1rem"
    height: "2.75rem"
  button-secondary:
    backgroundColor: "{colors.raised-panel}"
    textColor: "{colors.primary-ink}"
    typography: "{typography.label}"
    rounded: "{rounded.square}"
    padding: "0.7rem 1rem"
    height: "2.75rem"
  input:
    backgroundColor: "{colors.deep-canvas}"
    textColor: "{colors.primary-ink}"
    typography: "{typography.label}"
    rounded: "{rounded.square}"
    padding: "0.7rem 0.8rem"
    height: "2.75rem"
  panel:
    backgroundColor: "{colors.soft-panel}"
    textColor: "{colors.primary-ink}"
    rounded: "{rounded.square}"
    padding: "1.2rem"
---

# Design System: Artifact Platform

## Overview

**Creative North Star: "The Observatory Instrument Bay"**

Artifact Platform should feel like a precise piece of network infrastructure
that happens to be approachable: dark, dense, legible, and visibly alive. The
interface borrows the geometry of rack instrumentation and observatory readouts
without turning into science-fiction decoration. Every line, status light, and
monospace label communicates state or structure.

The catalog remains calm and scannable while the admin scope feels like the
same instrument with its service panel open. Avoid generic SaaS softness,
floating glass cards, decorative gradients, and oversized empty marketing
space.

**Key Characteristics:**

- Square, bordered surfaces arranged on an explicit grid.
- Condensed uppercase display type paired with humane body copy.
- Monospace telemetry labels and numeric readouts.
- Sparse lime signal color, cobalt peer identity, and semantic amber/red.
- Motion that suggests a scan or state transition and respects reduced motion.

## Colors

The palette is an ink-black instrument enclosure with cool steel dividers and
rare luminous signals.

### Primary

- **Mesh Signal** (`#b9ed70`): successful connectivity, primary actions,
  focus outlines, and the local mesh origin.

### Secondary

- **Peer Cobalt** (`#6ea0ff`): remote node identity, safe code references, and
  peer readouts.
- **Warning Amber** (`#f0be6b`): degraded connectivity and unsaved state.
- **Fault Red** (`#ff7b72`): validation faults, destructive controls, and
  failed saves.

### Neutral

- **Void Canvas** (`#090d12`) and **Deep Canvas** (`#05080b`): page and inset
  field backgrounds.
- **Instrument Panel** (`#101820`), **Raised Panel** (`#15212b`), and **Soft
  Panel** (`#0d141b`): structural surface hierarchy.
- **Primary Ink** (`#f1f5f3`), **Secondary Ink** (`#b5c0c8`), and **Telemetry
  Ink** (`#84919a`): primary, supporting, and metadata text.
- **Structural Line** (`#2c3a46`) and **Strong Line** (`#52616c`): dividers and
  enclosure boundaries.

**The Signal Discipline Rule.** Lime is reserved for focus, success, and the
single primary action in a region; its rarity makes it legible.

## Typography

**Display Font:** Barlow Semi Condensed (self-hosted, with Arial Narrow fallback)  
**Body Font:** Avenir Next (with Segoe UI and system sans fallbacks)  
**Label/Mono Font:** SFMono-Regular (with Consolas and Liberation Mono fallbacks)

**Character:** Display type is compact, forceful, and architectural. Body copy
stays familiar and readable; monospaced labels turn machine state into a
consistent telemetry layer.

### Hierarchy

- **Display** (800, `clamp(4rem, 9vw, 6rem)`, 0.8): uppercase hero titles,
  limited to a short phrase.
- **Headline** (800, `clamp(1.6rem, 3vw, 2.4rem)`): uppercase section names.
- **Title** (650, `clamp(1.05rem, 2vw, 1.3rem)`): artifact and peer identity.
- **Body** (400, `1rem`, 1.5): descriptions, with readable measures around
  44–64 characters.
- **Label** (700, `0.58rem–0.72rem`, tracked uppercase): controls, badges,
  statuses, and instrument captions.

**The Three-Voice Rule.** Use condensed display for hierarchy, the sans for
explanation, and mono only for state, identifiers, and controls.

## Layout

Content is capped at `94rem` with a fluid gutter of
`clamp(1rem, 4vw, 4.5rem)`. Desktop hero and catalog areas use deliberately
asymmetric two-column grids: narrative or section labels on the left and the
active instrument/list on the right. Major sections use a generous vertical
rhythm of `clamp(4.5rem, 8vw, 8rem)` while rows remain compact and separated by
one-pixel rules. At `760px`, all structural grids collapse to one column,
status readouts become two columns, and action groups stack without hiding
operational content.

## Elevation & Depth

The system is flat by default. Depth comes from tonal stacking, borders, the
subtle 2rem technical grid on the canvas, and a single ambient shadow on the
hero mesh instrument (`0 1.5rem 4rem rgba(0, 0, 0, 0.28)`). Status lights may
use a restrained colored glow; ordinary cards and form panels do not float.

**The Enclosure Rule.** A shadow marks a physical instrument or active signal,
never a routine list row.

## Shapes

Panels, buttons, fields, badges, and cards have square corners. One-pixel steel
borders create the enclosure language. Circles are reserved for literal status
lights and screw-like instrument details; they are not a general decoration.

## Components

### Buttons

- **Shape:** square, at least `2.75rem` high, with compact mono uppercase text.
- **Primary:** Mesh Signal fill and Deep Canvas text with a matching border.
- **Secondary:** Raised Panel fill, Primary Ink, and Strong Line border.
- **Hover / Focus:** use quick 160ms state changes and the universal 3px Mesh
  Signal focus outline with a 4px offset.
- **Text:** transparent destructive actions use Fault Red without pretending to
  be a primary control.

### Chips

- **Style:** transparent square badge, Strong Line border, and tracked mono
  label. Online state changes only the border and text to Mesh Signal.

### Cards / Containers

- **Corner Style:** square (`0`).
- **Background:** Soft or Instrument Panel depending on enclosure depth.
- **Shadow Strategy:** none except the signature mesh instrument.
- **Border:** one-pixel Structural or Strong Line.
- **Internal Padding:** normally `1rem–1.2rem`.

### Inputs / Fields

- **Style:** Deep Canvas fill, Structural Line border, square corners, and mono
  input text.
- **Focus:** 3px Mesh Signal outline at 4px offset.
- **Error / Disabled:** Fault Red helper text; disabled controls reduce opacity
  while preserving the label.

### Navigation

The top bar is a bordered enclosure with the compact signal-bar wordmark,
plain text links, and an inline connection readout. Links underline on hover;
navigation never becomes a floating pill.

### Artifact Rows

Rows are the primary browsing primitive: index, title/description, then a lime
launch mark. Hover adds a Raised Panel tone and translates the row by only
`0.35rem`, preserving the table-like rhythm.

## Do's and Don'ts

### Do:

- **Do** expose mesh and save state in plain language alongside visual signals.
- **Do** use one-pixel dividers to organize dense information.
- **Do** keep target sizes at least `2.75rem` and preserve visible keyboard
  focus.
- **Do** collapse grids before removing information on small screens.
- **Do** disable scanning animation through `prefers-reduced-motion`.

### Don't:

- **Don't** introduce rounded cards, pill navigation, or soft SaaS controls.
- **Don't** use Mesh Signal as broad decoration or paragraph text.
- **Don't** add ornamental charts, glows, or gradients that carry no state.
- **Don't** rely on color alone for online, warning, error, or save status.
- **Don't** use condensed display type for long prose or mono for descriptions.
