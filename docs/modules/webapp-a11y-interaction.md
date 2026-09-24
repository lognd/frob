# frob.webapp._a11y_interaction -- A11Y116-124 keyboard/focus/target-size/motion

One sentence: `frob.webapp._a11y_interaction` is the T-5321 leaf of the
`T-5140` web-app A11Y epic covering keyboard operability, focus
visibility, pointer target size, and motion-preference respect -- nine
rule ids in the reserved `A11Y1xx` block, distinct from T-5313's
`alt`/`aria-label`/heading-level/`<html lang>` substrate.

## Gate wiring

`frob.gates._a11y_gate` (T-5323) discovers every module in the
`frob.webapp` package whose name starts with the `_a11y_` prefix and
exposes a module-level `a11y_findings(ctx, frameworks) ->
tuple[Violation, ...]` hook, folding the results into one gate run. This
module's `a11y_findings` is that hook: `ctx` is one already-parsed file
(a `frob.webapp._a11y_structure.A11yFileContext` -- file path, language
label, raw source bytes, and the tree-sitter root node), handed to every
discovered hook by the gate's own single parse-once walk over every
git-tracked file its file-extension list names, and `frameworks` is
likewise already-detected by the gate (once per `frob check` run, not
once per leaf module). An empty `frameworks` short-circuits to `()`
before `ctx.source` is even decoded.

KNOWN GAP: that gate-owned file-extension list currently covers only
html/vue/jsx/tsx, not CSS/SCSS -- this leaf's four CSS-declaration rules
(A11Y117/120/121/122, below) are fully implemented and unit-tested
against a directly-constructed CSS `A11yFileContext`, but the real gate
never hands this hook a CSS file today. Widening that list lives in
`src/frob/gates/**`, outside this ticket's declared scope; T-draft-2c8aa622
is filed to close the gap.

## Detection approach

TEXT-REGEX over `ctx.source` decoded to text (not `ctx.root`'s
tree-sitter node tree), the same posture `frob.webapp._websec_sinks`
(WEBSEC104-106) already establishes for checks whose declared scope is
not a tree-sitter-parseable shape frob has a grammar for: `frob.lang`'s
CSS walker (T-5303) walks selectors into `RawSymbol`s for the graph
symbol index, not parsed declaration values, and several of these rules
need exactly a declaration value (an `outline` value, a pixel dimension)
or a link's own text content.

## Rule ids

- **A11Y116** -- an html-family page with a `<body>` but no skip-link
  anchor (`<a href="#...">` whose text mentions "skip"; WCAG SC 2.4.1).
- **A11Y117** -- a `:focus` CSS rule suppressing the outline
  (`outline: none`/`outline: 0`) with no `:focus-visible` rule anywhere
  in the same file supplying a real replacement (WCAG SC 2.4.7).
- **A11Y118** -- a positive `tabindex`/`tabIndex` (WCAG SC 2.4.3).
- **A11Y119** -- `aria-hidden="true"` on a naturally-focusable element
  (`a[href]`, `button`, `input`, `select`, `textarea`).
- **A11Y120** -- a `button`/`.btn`/`[role="button"]`-shaped CSS rule
  declaring a width/height/min-width/min-height below 24 CSS px (WCAG SC
  2.5.8, Target Size Minimum, AA).
- **A11Y121** -- the same selector family declaring a dimension between
  24 and 44 CSS px (WCAG SC 2.5.5, Target Size Enhanced, AAA) -- a
  separate rule id from A11Y120 so a repo can waive the AAA-only
  threshold independently of the AA floor.
- **A11Y122** -- `animation`/`transition` declared with no
  `prefers-reduced-motion` media query anywhere in the file (WCAG SC
  2.3.3).
- **A11Y123** -- `<video>`/`<audio autoplay>` with no `controls`
  attribute on the same tag (WCAG SC 1.4.2/2.2.2).
- **A11Y124** -- a `<video>` with no `<track kind="captions">` child, or
  a self-closing `<video/>` (WCAG SC 1.2.2).

Every rule id here is WARN-tier at first turn-on (T-0688/T-0973 posture);
a real fix-or-waive pass over the first measured hit set decides whether
any promote to ERROR.

## Public API

- `a11y_findings(ctx: A11yFileContext, frameworks: frozenset[FrameworkKind])
  -> tuple[Violation, ...]` -- every A11Y116-124 finding in the single
  already-parsed file `ctx` names.

## Fixtures

`tests/fixtures/webapp/a11y1xx/interaction/<ruleid>_positive/` and
`<ruleid>_negative/`, one positive and one negative fixture per rule id,
covered by `tests/unit/test_webapp_a11y_interaction.py`.
