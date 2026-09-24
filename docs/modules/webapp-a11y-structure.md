# frob.webapp._a11y_structure / frob.gates._a11y_gate -- A11Y101-115 structure/forms

One sentence: `frob.webapp._a11y_structure.a11y_findings` implements the
non-text-content/document-structure/form-labeling half of the T-5146 WCAG
2.2 A/AA corpus (A11Y101-115) over `frob.webapp._a11y_substrate`'s (T-5313)
tree-query helpers -- see `docs/modules/webapp-a11y.md` for that
substrate's own query-helper reference -- and `frob.gates._a11y_gate.
a11y_gate` (T-5323) is the A11Y family's first gate registration -- it
owns the one discovery edit every future A11Y rule module opts into for
free.

This is one of seven sibling web-app-lint story leaves under the T-5140
epic (docs/modules/webapp.md's own scope: framework detection only, not
any individual rule family). A follow-up ticket links all seven family
docs (WEBSEC, session/CSRF, response headers, authz, COMPLY, this one,
SEO/WEBPERF) from webapp.md once all seven land.

## The hook protocol

Any module in the `frob.webapp` package whose name starts with the
`a11y` prefix (e.g. `frob.webapp._a11y_structure`) and exposes a
module-level

```python
def a11y_findings(
    ctx: A11yFileContext, frameworks: frozenset[FrameworkKind]
) -> tuple[Violation, ...]: ...
```

is discovered and called by `frob.gates._a11y_gate.a11y_gate` for every
git-tracked html-family/jsx-family file (`.html`, `.htm`, `.vue`, `.jsx`,
`.tsx`) in the repo, once per file. `_a11y_gate.py` parses each file
exactly once via `frob.lang.raw_tree` and builds one
`A11yFileContext` (repo-relative `file`, `language` label, raw `source`
bytes, and the tree-sitter `root` `Node`) that every discovered hook
receives -- no hook module re-parses the same file itself.

Discovery is `pkgutil.iter_modules` over the `frob.webapp` package,
filtered to submodule names starting with the `a11y` prefix, each match
imported via `importlib.import_module` and checked for the
`a11y_findings` attribute.
A matching module with no hook (e.g. `_a11y_substrate` itself, which is
pure query helpers with no `a11y_findings` of its own) is logged at
WARNING and skipped, never silently dropped -- this closes the
"catalogued is not enforced" trap the SUBSTRATE-FANOUT lessons name:
`@gate`/registry declaration alone does not make a detector run, only
this gate's own runtime discovery loop does.

A second A11Y rule module (a future WCAG chunk) needs ZERO edits to
`frob.gates._a11y_gate.a11y_gate` to start contributing violations: it
only has to live in the `frob.webapp` package with a name starting in
the same `a11y` prefix and expose the hook.

## Framework gating

`a11y_gate(root)` calls `frob.webapp._detect.detect_frameworks` first and
returns `()` immediately for a repo with no detected web framework -- the
same short-circuit every WEBSEC/COMPLY/A11Y/SEO/WEBPERF family uses
(T-5302). `a11y_findings` itself also checks `frameworks` and returns `()`
for an empty set, so a hook called directly (e.g. from a test) carries the
same contract as the gate's own short-circuit.

## Rule catalog (WCAG 2.2 success criterion in parens)

| rule | check |
| --- | --- |
| A11Y101 | `<img>` missing `alt` (SC 1.1.1) |
| A11Y102 | `<svg role="img">` missing an accessible name (SC 1.1.1) |
| A11Y103 | heading level skips a level, e.g. h1 straight to h3 (SC 1.3.1) |
| A11Y104 | more than one `<h1>` on the page (SC 1.3.1) |
| A11Y105 | `<title>` missing (SC 2.4.2) |
| A11Y106 | `<html>` missing a `lang` attribute (SC 3.1.1) |
| A11Y107 | `<html lang="">` present but empty (SC 3.1.1) |
| A11Y108 | `<a>` with no accessible name (SC 2.4.4) |
| A11Y109 | `<button>` with no accessible name (SC 2.4.4) |
| A11Y110 | `<a>`/`<button>` accessible name is a known generic phrase, e.g. "click here" (SC 2.4.4) |
| A11Y111 | form input with no associated label (`<label for>`, `aria-label`, `aria-labelledby`) |
| A11Y112 | identity-autofill input missing `autocomplete` (SC 1.3.5) |
| A11Y113 | duplicate `id` attribute value in one file |
| A11Y114 | `role="..."` value not in the WAI-ARIA 1.2 role vocabulary |
| A11Y115 | `aria-*` attribute name not in the WAI-ARIA 1.2 state/property vocabulary |

Each is WARN-tier at first turn-on -- the same T-0688/T-0973 promotion
posture `taint_gate`/`opaque_gate` already follow for a brand-new
structural rule: a real fix-or-waive pass over the first measured hit set
decides whether ERROR is safe.

## Public API

- `A11yFileContext` (`src/frob/webapp/_a11y_structure.py`) -- one parsed
  file: `file`, `language`, `source`, `root`.
- `a11y_findings(ctx, frameworks) -> tuple[Violation, ...]` -- A11Y101-115
  over one `A11yFileContext`.
- `frob.gates._a11y_gate.a11y_gate(root: Path) -> tuple[Violation, ...]`
  -- the gate job: walks, parses, discovers hooks, calls each.

### Substrate additions (T-5323)

- `frob.webapp._a11y_substrate.all_elements(root, language, source)` --
  the unfiltered element enumeration `elements_with_attribute`/
  `elements_missing_attribute` both specialize; A11Y111-115 use it
  directly for checks that need to see every element regardless of tag
  or attribute presence (duplicate ids, ARIA role/attribute validation,
  accessible-name computation).

## Fixtures

`tests/fixtures/webapp/a11y1xx/structure/**` -- one positive (violation
present) and one negative (clean) fixture per rule id, named
`<rule-id>_violation.html`/`<rule-id>_clean.html` (or `.jsx`/`.vue` where
the rule needs a non-html grammar to exercise).
