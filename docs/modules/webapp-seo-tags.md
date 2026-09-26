# frob.webapp._seo_tags -- SEO101-112 per-page tags

One sentence: `frob.webapp._seo_tags.seo_tag_findings` reuses T-5364's
`frob.webapp._seo_substrate.extract_page_metadata`/
`build_duplicate_title_index` for every fact it needs -- unique
title/meta-description per route, the four `og:*` tags, canonical link,
favicon, and JSON-LD `LocalBusiness` required properties -- and never
re-parses a `<head>` block or stands up its own tree-sitter walk.

This is a downstream leaf of the T-5140 web-app epic's substrate wave
(docs/modules/webapp.md's own scope: framework detection only, not any
individual rule family), and of T-5364's SEO/WEBPERF metadata-
extraction substrate specifically.

## Framework gating

`seo_tag_findings(root)` calls `frob.webapp._detect.detect_frameworks`
first and returns `()` immediately for a repo with no detected web
framework -- the same short-circuit every WEBSEC/COMPLY/A11Y/SEO/
WEBPERF family uses (T-5302). This module never re-implements framework
sniffing.

## Discovery convention -- READ THIS FIRST if wiring a caller

`docs/modules/webapp-seo.md` (T-5364's substrate doc) defines NO hook
convention for a leaf to opt into a gate. Unlike A11Y (which stood up
its own `frob.gates._a11y_gate` pkgutil-discovery gate, T-5323) or
WEBSEC (`frob.gates._taint_gate`'s pkgutil discovery over every
`frob.webapp._websec_*` module, T-5308), no SEO-family discovery gate
exists yet on `dev` as of this leaf.

This module's hook is named `websec_findings(root, frameworks) ->
tuple[Violation, ...]` to match `frob.gates._taint_gate`'s established
discovery SHAPE exactly (same signature, same `Violation`/`Severity`
wrapping), per this ticket's own coordinator direction to fall back to
that convention when the substrate doc defines none. **This name alone
does NOT wire it into `taint_gate`**: `_taint_gate._discover_websec_hook_modules`
only scans `frob.webapp` submodules whose NAME starts with `_websec_`
(`_WEBSEC_MODULE_PREFIX`), and `_seo_tags` does not match that prefix.
No live gate currently calls `websec_findings` here -- calling
`seo_tag_findings`/`websec_findings` directly (as this module's own
test suite does) is the only way to run these checks today.

The correct fix is real gate wiring for this family -- either a new
discovery gate mirroring the A11Y family's own "first leaf owns the
one discovery edit" pkgutil pattern (T-5323), or (as later re-scoped)
widening the existing WEBSEC discovery mechanism's own matched-module-
prefix set to also cover this family -- filed as follow-up scope
rather than widened into this ticket, since a shared gate-registration
file touches every concurrent WEBSEC/COMPLY/A11Y/SEO/WEBPERF leaf (see
the T-5374 Done report for the follow-up ticket id).

## Rule catalog

| rule | check | detection |
| --- | --- | --- |
| SEO101 | a `<title>` shared by two or more routes | `build_duplicate_title_index`, reused unchanged |
| SEO102 | a meta description shared by two or more routes | local duplicate-index helper over `PageMetadata.meta`, same shape as SEO101's |
| SEO103 | no `<meta property="og:title">` | per-page `PageMetadata.meta` check |
| SEO104 | no `<meta property="og:type">` | per-page `PageMetadata.meta` check |
| SEO105 | no `<meta property="og:image">` | per-page `PageMetadata.meta` check |
| SEO106 | no `<meta property="og:url">` | per-page `PageMetadata.meta` check |
| SEO107 | no `<link rel="canonical">` | per-page `PageMetadata.links` check |
| SEO108 | no `<link rel="icon">`/`<link rel="shortcut icon">` (favicon) | per-page `PageMetadata.links` check |
| SEO109 | a JSON-LD block that is not valid JSON | `json.loads` over `PageMetadata.json_ld` |
| SEO110 | a JSON-LD `LocalBusiness` block with no `name` | same, `@type == "LocalBusiness"` only |
| SEO111 | a JSON-LD `LocalBusiness` block with no `address` | same |
| SEO112 | a JSON-LD `LocalBusiness` block with no `telephone` | same |

All twelve reserved ids (`SEO101`-`SEO112`) are used. `html-lang`
cross-refs A11Y104's own rule id (the ticket body's own
cross-reference) and is not duplicated here.

SEO110-112 only fire for a JSON-LD block whose `@type` is exactly
`"LocalBusiness"` -- a block for a different `@type` (e.g.
`"Organization"`, `_seo_substrate`'s own `home.html` fixture) carries no
LocalBusiness-shaped signal and is silently skipped, not flagged.

## Severity

WARN-tier at first turn-on -- the same T-0688/T-0973 promotion posture
`taint_gate`/`opaque_gate`/every sibling WEBSEC/SEO family already
follows for a brand-new structural rule.

## Public API

- `WebsecSeoTagFinding` (`src/frob/webapp/_seo_tags.py`) -- one finding:
  `rule`, `file`, `line`, `message`.
- `seo_tag_findings(root: Path) -> tuple[WebsecSeoTagFinding, ...]` --
  every SEO101-112 finding under `root`.
- `websec_findings(root: Path, frameworks: frozenset[FrameworkKind]) ->
  tuple[frob.findings.Violation, ...]` -- see "Discovery convention"
  above; a thin `Violation`-wrapping caller over `seo_tag_findings`,
  not currently reachable through any live gate.

## Tests and fixtures

`tests/unit/test_seo_tags.py` -- one positive-control and one
negative-control fixture per rule under
`tests/fixtures/webapp/seo1xx/tags/seo1{01..12}_{positive,negative}/`,
each carrying a minimal Flask framework marker (`requirements.txt`
naming `flask`, so `detect_frameworks` fires) plus exactly the
head/JSON-LD shape under test. SEO101/SEO102's fixtures carry TWO route
files (a shared title/description in the positive case, distinct ones
in the negative); every other rule's fixtures carry one `page.html`
with a full set of tags, minus (positive) or including (negative) the
one under test. This subdir (`tags/`) is this ticket's own fixture
scope, distinct from sibling `seo1xx/spam/` (T-5365) and `seo1xx/crawl/`
(T-5362) subdirs under the same parent, and from T-5364's own
`seo1xx/routes/` substrate fixtures (a different subdir again).

Because no live gate discovers `websec_findings` (see above), this
suite has no `taint_gate`-style end-to-end positive-control test; the
closest equivalent is `test_websec_findings_emits_violation_when_called_directly`,
which calls the hook directly and asserts on its real `Violation`
output.

frob:ticket T-5374
