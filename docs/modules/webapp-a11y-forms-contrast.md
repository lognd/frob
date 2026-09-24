# frob.webapp._a11y_forms_contrast -- A11Y129-135: redundant entry, accessible authentication, contrast

One sentence: `frob.webapp._a11y_forms_contrast` implements the three
WCAG 2.2 success criteria the T-5140 web-app A11Y epic reserved
`A11Y129`-`A11Y135` for -- redundant entry (SC 3.3.7), accessible
authentication (SC 3.3.8), and color contrast (SC 1.4.3) -- and exposes
the discovery hook `frob.gates._a11y_gate.a11y_gate` (T-5323) wires up.

## Rule ids

| Rule    | WCAG SC | Signal |
| ------- | ------- | ------ |
| A11Y129 | 3.3.7   | An `<input>` `name` recurs across the file (a multi-step form asking for the same info twice) and a later occurrence carries no `autocomplete` attribute. |
| A11Y130 | 3.3.7   | A recurring `<input>` `name`'s first occurrence has a literal `value`, and a later occurrence does not carry it forward (not pre-filled/re-displayed). |
| A11Y131 | 3.3.8   | A CAPTCHA-style marker (`class`/`id`/`data-*` containing `captcha`) with no alternative-method marker (`auth-alt`/`alt-auth`/`alternative`) anywhere in the file. |
| A11Y132 | 3.3.8   | A `type="password"` `<input>` with an `onpaste` handler and no `data-allow-paste="true"` escape hatch -- blocking paste forces the user to recall the value from memory, itself a cognitive-function test. |
| A11Y133 | 1.4.3   | A CSS/SCSS rule's declared `color`+`background-color` pair (literal hex/`rgb()` only) has a contrast ratio below 4.5:1 for normal-weight text. |
| A11Y134 | 1.4.3   | Same as A11Y133 but for text WCAG classifies as "large" (`>=24px`, or `>=18.66px` and bold) -- threshold 3:1. |
| A11Y135 | 1.4.3   | A CSS/SCSS rule's declared `border-color`+`background-color` pair (a UI component outline) has a contrast ratio below 3:1. |

## Scan shape

`frob.gates._a11y_gate.a11y_gate` (T-5323) walks every git-tracked
html-family/jsx-family file once, parses it once, and hands each
discovered hook module a shared `A11yFileContext`
(`frob.webapp._a11y_structure.A11yFileContext`, already-parsed
file/language/source/root-node) plus the repo's detected framework
set -- one call per file, no filesystem access of its own in this
module.

Redundant entry and accessible authentication are shallow regex scans
over that context's decoded source text (the same predictable, false-
negative-tolerant posture `frob.webapp._comply_substrate`/
`_websec_sinks` already take for their own text-level heuristics) -- no
dependency on `frob.webapp._a11y_substrate`'s tree-sitter query helpers,
since neither signal needs a parsed element tree to answer.

Contrast DOES need a real grammar: declared colors can be `rgb(...)`
call expressions, not just bare hex literals, so this branch walks the
already-parsed css/scss tree-sitter node the context carries (T-5303's
grammar) rather than re-parsing.

Known gap: the gate's own tracked-file walk covers only
`.html`/`.htm`/`.vue`/`.jsx`/`.tsx`, so it never hands this module a
`.css`/`.scss` context today -- A11Y133-135 are fully implemented and
unit-tested directly, but cannot fire through the live gate until a
follow-up ticket widens the gate's own file-extension list (out of this
ticket's scope; the gate module itself is off-limits here).

## Public API

- `contrast_ratio(rgb_a, rgb_b) -> float`: the WCAG relative-luminance
  contrast ratio between two `(r, g, b)` triples (`0-255` each) -- a
  standalone pure function with no file/tree dependency, reusable by any
  caller with its own two colors (T-5147/SEO-WEBPERF names this as a
  planned second consumer).
- `a11y_findings(ctx, frameworks) -> tuple[Violation, ...]`: every
  A11Y129-135 finding in one already-parsed file context `ctx`. Short-
  circuits to `()` when `frameworks` is empty -- the gate has already run
  `frob.webapp._detect.detect_frameworks` once and passes the result in;
  this module never re-detects frameworks itself.

## Fixtures

One `a11y1NN_positive`/`a11y1NN_negative` directory pair per rule id
under `tests/fixtures/webapp/a11y1xx/forms_contrast/`, mirroring
`tests/fixtures/webapp/websec1xx/`'s own per-rule layout -- each
directory holds exactly one fixture file, parsed directly into the
`A11yFileContext` shape the real gate would hand this module's hook.
