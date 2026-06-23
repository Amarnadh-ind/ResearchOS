# Design System: ResearchOS — Autonomous Research Laboratory

## 1. Visual Theme & Atmosphere

A restrained, gallery-airy interface with confident asymmetric layouts and fluid spring-physics motion. The atmosphere is clinical yet warm — like a well-lit architecture studio. The design should feel like a sophisticated research environment where every element serves a purpose and contributes to the overall experience of discovery and analysis.

## 2. Color Palette & Roles

- **Canvas White** (#F9FAFB) — Primary background surface
- **Pure Surface** (#FFFFFF) — Card and container fill
- **Deep Charcoal Ink** (#0F172A) — Primary text, Zinc-950 depth
- **Muted Steel** (#475569) — Secondary text, descriptions, metadata
- **Whisper Border** (rgba(226,232,240,0.5)) — Card borders, 1px structural lines
- **Research Blue** (#6366F1) — Single accent for CTAs, active states, focus rings

## 3. Typography Rules

- **Display:** Playfair Display — Track-tight, controlled scale, weight-driven hierarchy
- **Body:** Space Grotesk — Relaxed leading, 65ch max-width, neutral secondary color
- **Mono:** JetBrains Mono — For code, metadata, timestamps, high-density numbers
- **Banned:** Inter, generic system fonts for premium contexts. Serif fonts banned in dashboards.

## 4. Component Stylings

* **Buttons:** Flat, no outer glow. Tactile -1px translate on active. Accent fill for primary, ghost/outline for secondary.
* **Cards:** Generously rounded corners (2.5rem). Diffused whisper shadow. Used only when elevation serves hierarchy. High-density: replace with border-top dividers.
* **Inputs:** Label above, error below. Focus ring in accent color. No floating labels.
* **Loaders:** Skeletal shimmer matching exact layout dimensions. No circular spinners.
* **Empty States:** Composed, illustrated compositions — not just "No data" text.

## 5. Layout Principles

(Grid-first responsive architecture. Asymmetric splits for Hero sections. Strict single-column collapse below 768px. Max-width containment. No flexbox percentage math. Generous internal padding.)

## 6. Motion & Interaction

(Spring physics for all interactive elements. Staggered cascade reveals. Perpetual micro-loops on active dashboard components. Hardware-accelerated transforms only. Isolated Client Components for CPU-heavy animations.)

## 7. Anti-Patterns (Banned)

(Explicit list of forbidden patterns: no emojis, no Inter, no pure black, no neon glows, no 3-column equal grids, no AI copywriting clichés, no generic placeholder names, no broken image links.)
