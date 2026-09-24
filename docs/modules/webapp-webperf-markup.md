# frob.webapp._webperf_markup -- WEBPERF101-106/108 Core Web Vitals causes in markup

One sentence: seven static, shallow scans over `.html`/`.jsx` route
files, CSS, and webpack/vite config text, each flagging one markup-level
cause of a Core Web Vitals regression (CLS/LCP) -- WEBPERF107 is
deliberately excluded (see below).

This is a follow-up leaf of the WEBSEC/COMPLY/A11Y/SEO/WEBPERF epic's
shared `frob.webapp`/`frob.lang` scaffolding (`docs/modules/webapp.md`,
T-5302/T-5300), blocked by T-5364's `frob.webapp._seo_substrate` (the
`<head>` metadata substrate this module reuses rather than
re-implementing). Sibling ticket T-5366 owns the SERVER half of the
`webperf1xx` rule family (`tests/fixtures/webapp/webperf1xx/server/**`);
this module and its fixtures live entirely under
`tests/fixtures/webapp/webperf1xx/markup/**`.

## Public API

```python
class WebperfMarkupFinding:   # frozen dataclass
    rule: str
    file: str
    line: int
    message: str

def webperf_markup_findings(root: Path) -> tuple[WebperfMarkupFinding, ...]
def websec_findings(root: Path, frameworks: frozenset[FrameworkKind]) -> tuple[Violation, ...]
```

`src/frob/webapp/_webperf_markup.py`.

## Rule ids

- **WEBPERF101** -- an `<img>` missing `width` or `height`: the browser
  cannot reserve layout space before the image loads (the canonical CLS
  cause).
- **WEBPERF102** -- an `<img>`/`<iframe>` with no `loading="lazy"` and no
  explicit `loading="eager"`/`fetchpriority="high"` escape hatch: an
  offscreen element forcing eager network/paint work.
- **WEBPERF103** -- an `<img>` missing `srcset`: no responsive source
  set, so every viewport downloads the same, possibly oversized, asset.
- **WEBPERF104** -- an `@font-face` CSS rule with no `font-display`: a
  custom font blocks text rendering with no documented fallback strategy
  (FOIT instead of a declared swap/fallback).
- **WEBPERF105** -- a `<script src="...">` inside `<head>`/`<Head>` with
  neither `defer` nor `async`: a synchronous, render-blocking script.
- **WEBPERF106** -- a `webpack.config.{js,ts,mjs,cjs}`/
  `vite.config.{js,ts,mjs,cjs}` with no bundle-size-budget assertion
  (`maxAssetSize`/`maxEntrypointSize`/`chunkSizeWarningLimit`): nothing
  catches an unbounded bundle-size regression at build time.
- **WEBPERF108** -- a document with no `<meta name="viewport" ...>`
  anywhere in `<head>`: mobile layout falls back to a desktop-width
  viewport, a common CLS/zoom cause on narrow screens.

### WEBPERF107 -- deliberately not implemented here

The ticket body's own scope note: "source-maps-in-prod cross-refs
T-5143-3, not duplicated." T-5143-3 already owns detecting a production
build serving `.map` files; this module never re-implements that check
under a second rule id, and `webperf_markup_findings`/`websec_findings`
never emit `WEBPERF107`. The rule id stays reserved in `_KNOWN_GATE_RULES`
(`frob.gates._waive`) for that other leaf.

## Substrate reuse

Parsing goes through `frob.lang.raw_tree` (T-5300's single parse
dispatch) via `frob.webapp._seo_substrate`'s own node-shape helpers
(`_HTML_ELEMENT_TYPES`/`_JSX_ELEMENT_TYPES`, `_html_tag_name`/
`_html_attrs`, `_jsx_tag_name`/`_jsx_attrs`, `_find_head` and the
HTML/JSX head-children iterators) -- this module never stands up its own
tree-sitter `Parser` and never re-derives an element's tag name or
attribute map from raw node text.

`_seo_substrate`'s own SCOPE note (only `<head>` contents) applies to the
two head-only rules here (WEBPERF105/108). WEBPERF101-103 walk the WHOLE
document body (every `<img>`/`<iframe>` element, not just ones under
`<head>`) via `_iter_elements`, a depth-first walker built from the SAME
element-type/tag-name/attrs primitives -- a generalization of
`_seo_substrate._find_head`'s single-target search, not a duplicate
implementation of tree-sitter node walking.

WEBPERF104 (CSS `@font-face`) and WEBPERF106 (webpack/vite config text)
are plain regex scans over file text -- CSS/JS config grammars are out of
`_seo_substrate`'s scope, same posture `frob.webapp._websec_headers_rules`
already takes for a target its own substrate does not cover (its own
module docstring: "own tiny private copy, not a cross-module private
import" -- here, a shallow text scan where no tree-sitter substrate
exists at all, not a duplicate of one that does).

## Gate discovery

`frob.gates._taint_gate._discover_websec_hook_modules` only scans
`frob.webapp._websec_*` submodules (`_WEBSEC_MODULE_PREFIX = "_websec_"`)
as of this ticket. This module follows the SAME
`websec_findings(root, frameworks) -> tuple[Violation, ...]` hook shape
every WEBSEC/SEO/WEBPERF sibling uses, so it needs ZERO further wiring
once **T-draft-553232aa** widens discovery to also match the `_webperf_`
prefix.

Until T-draft-553232aa lands, `websec_findings` is reachable directly
(this module's own test suite calls it) but is NOT yet folded into
`frob check`'s live gate scan. `tests/unit/test_webapp_webperf_markup.py::
test_webperf_markup_reachable_via_gate_discovery_end_to_end` is the
end-to-end control for this gap: an `xfail(strict=True)` test that calls
`frob.gates._taint_gate.taint_gate` directly over a WEBPERF101-positive
fixture and asserts a `WEBPERF101` violation comes back. It fails today
(not discovered) and is marked `strict=True` so the MOMENT
T-draft-553232aa lands and discovery widens, this test starts passing and
the strict xfail itself fails loudly -- forcing the marker's removal
instead of the gap going unnoticed.
