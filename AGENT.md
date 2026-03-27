# MindAble — Frontend Rules

## What We're Building

MindAble is an AI-powered job platform for neurodivergent people and those managing mental health conditions. The frontend must reflect that — every page should feel calm, safe, and human. No overwhelming layouts, no aggressive CTAs, no corporate coldness.

**Stack: HTML + CSS + Vanilla JS only.** No frameworks, no build tools, no exceptions.

---

## Behaviour

- **Read before touching.** Always read the full file before making any edit.
- **Never rewrite what works.** If a component exists and functions correctly, extend it — don't replace it.
- **Never invent UI.** Don't add sections, copy, buttons, or components that weren't asked for.
- **Never break consistency.** Every page must feel like it belongs to the same product. If a pattern exists in `home.html` or `auth.html`, follow it everywhere.
- **Ask before removing anything.** Deletions must be explicitly requested.
- **UI copy must match the brand voice** — warm, direct, empowering. Never clinical, never corporate, never pushy.

---

## Hard Constraints

- **No JS frameworks.** No React, Vue, Alpine, Svelte, or any other library. Vanilla JS only.
- **No CSS frameworks.** No Tailwind, Bootstrap, or any utility library. The design system is hand-rolled.
- **No inline styles** unless a value is genuinely dynamic (e.g. a width set by JS). All styles belong in `<style>` or an external `.css` file.
- **No placeholder-only inputs.** Every `<input>` and `<textarea>` must have a visible `<label>`.
- **No hardcoded colours.** Every colour value must come from a CSS variable defined in `:root`. No exceptions.
- **No `!important`.** If you need it, the selector structure is wrong.
- **No `var`.** Use `const` by default, `let` when reassignment is needed.
- **No `console.log` in finished code.**
- Every page must have the **aura background blobs**.
- Every page must have the **standard `<nav>`** — copy it from an existing page, never rewrite it.
- All interactive elements must have both `:hover` and `:focus-visible` states.
- `scroll-behavior: smooth` must be set on `html`. All internal links use `#id` anchors.

## Coding style
## Code Style

### HTML
- 2-space indentation.
- Semantic elements first — `<nav>`, `<section>`, `<main>`, `<footer>`. Use `<div>` only when nothing semantic fits.
- Class names follow BEM-lite: `.feat-card`, `.feat-card-icon`, `.feat-card--wide`.
- Section breaks use: `<!-- ═══ SECTION NAME ═══ -->`.
- Group `<head>` in this order: charset → viewport → title → fonts → styles.

### CSS
- All values (colours, radii, shadows, gradients) must come from `:root` variables. Never hardcode them.
- Property order within every rule: layout → box model → typography → visual → animation.
- Transitions: `0.2s ease` for hovers, `0.6s ease` for reveal animations.
- Media queries at the bottom of the file. One mobile breakpoint: `max-width: 900px`.
- No `!important`. If you need it, the selector is wrong.

### JavaScript
- `const` by default, `let` when reassignment is needed, never `var`.
- Functions named with verbs: `handleLogin()`, `goStep()`, `togglePassword()`.
- Event listeners over inline `onclick` — unless the pattern already exists in that file, then keep it consistent.
- All scripts placed before `</body>`.
- No `console.log` in finished code.

### What "done" looks like
- No hardcoded colour or spacing values.
- Every input has a visible `<label>`.
- Every interactive element has `:hover` and `:focus-visible` states.
- No unused variables, dead code, or leftover logs.

##Visual Design 
-Stick to the same design on already uploaded html,css and js files in the folder frontend