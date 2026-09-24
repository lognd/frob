# frob.webapp._seo_crawl -- SEO121-126 crawl/discovery config

One sentence: `frob.webapp._seo_crawl.seo_crawl_findings` checks
`robots.txt` for malformed lines and an explicit Google-Extended
AI-training-opt-out decision record, `sitemap.xml` against the
sitemaps.org schema (stdlib `xml.etree.ElementTree`), `llms.txt`
advisory-only presence, `hreflang` alternate-link config, and
canonical links carrying a query string -- reusing T-5364's
`frob.webapp._seo_substrate.extract_page_metadata` for the
canonical-link half, the same substrate the sibling SEO tags (T-5374)
and spam-policy (T-5365) leaves already build on.

This is a downstream leaf of the T-5140 web-app epic's substrate wave
(docs/modules/webapp.md's own scope: framework detection only, not any
individual rule family), and of T-5364's SEO/WEBPERF metadata-
extraction substrate specifically.

## Framework gating

`seo_crawl_findings(root)` calls `frob.webapp._detect.detect_frameworks`
first and returns `()` immediately for a repo with no detected web
framework -- the same short-circuit every WEBSEC/COMPLY/A11Y/SEO/
WEBPERF family uses (T-5302).

## Discovery convention

Same posture the sibling SEO leaves (tags/spam -- T-5374/T-5365)
document in full for their own doc pages:
`docs/modules/webapp-seo.md` defines no leaf-hook convention, and
`frob.gates._taint_gate`'s pkgutil discovery only scans
`frob.webapp._websec_*`-prefixed modules -- `_seo_crawl` does not
match, so this module's `websec_findings` hook is not currently
auto-discovered by any live gate either.

T-draft-553232aa (filed by T-5374) is the actual fix, narrowed by the
coordinator's plan: T-5372 already generalized `_taint_gate`'s
discovered-module-prefix tuple to `("_websec_", "_comply_")`, so
T-draft-553232aa becomes a small leaf that widens that same tuple to
also include `"_seo_"`/`"_webperf_"` plus one end-to-end control per
family, rather than a whole new gate module. Once it lands, this
module's `websec_findings` hook is discovered for free.

## Rule catalog

| rule | check | detection |
| --- | --- | --- |
| SEO121 | a `robots.txt` line that is neither blank, a `#` comment, nor a `Directive: value` shape -- malformed | line-oriented text scan (the ticket body's own framing: no grammar needed) |
| SEO122 | a `robots.txt` present with no explicit `User-agent: Google-Extended` stanza -- no AI-training-opt-out decision recorded | text-regex over `robots.txt` |
| SEO123 | a `sitemap.xml` that is not valid XML, has a non-`urlset` root, or a `<url>` with no `<loc>` -- sitemaps.org schema validation | stdlib `xml.etree.ElementTree` (the ticket body's own framing: no third-party XML dependency) |
| SEO124 | no tracked `llms.txt` at all -- advisory-only presence | tracked-file-name check |
| SEO125 | 2+ `<link rel="alternate" hreflang="...">` tags with no `hreflang="x-default"` | text-regex over tracked `.html`/`.jsx` |
| SEO126 | a `<link rel="canonical">` href carrying a query string | `extract_page_metadata`'s `PageMetadata.links` |

Six of the reserved `SEO121`-`SEO127` seven-id block are used; `SEO127`
is left unimplemented -- filed as follow-up scope, see the T-5362 Done
report for the ticket id.

SEO122 treats EITHER an explicit `Allow` or `Disallow` for
`Google-Extended` as satisfying the check -- the finding is the absence
of any decision, not a particular decision.

`hreflang` is read via a small local text-regex over the raw file
rather than through `_seo_substrate.LinkTag` (which carries only
`rel`/`href`, no `hreflang` attribute) -- widening that shared model for
a single consumer was judged out of scope; see the module docstring.

## Severity

WARN-tier at first turn-on -- the same T-0688/T-0973 promotion posture
`taint_gate`/`opaque_gate`/every sibling WEBSEC/SEO family already
follows for a brand-new structural rule. SEO124 stays WARN-tier
permanently (advisory-only per the ticket body, not a candidate for
ERROR promotion by this leaf).

## Public API

- `WebsecSeoCrawlFinding` (`src/frob/webapp/_seo_crawl.py`) -- one
  finding: `rule`, `file`, `line`, `message`.
- `seo_crawl_findings(root: Path) -> tuple[WebsecSeoCrawlFinding, ...]`
  -- every SEO121-126 finding under `root`.
- `websec_findings(root: Path, frameworks: frozenset[FrameworkKind]) ->
  tuple[frob.findings.Violation, ...]` -- see "Discovery convention"
  above; a thin `Violation`-wrapping caller over `seo_crawl_findings`,
  not currently reachable through any live gate.

## Tests and fixtures

`tests/unit/test_seo_crawl.py` -- one positive-control and one
negative-control fixture per rule under
`tests/fixtures/webapp/seo1xx/crawl/seo1{21..26}_{positive,negative}/`,
each carrying a minimal Flask framework marker (`requirements.txt`
naming `flask`, so `detect_frameworks` fires) plus exactly the
`robots.txt`/`sitemap.xml`/`llms.txt`/page shape under test. This
subdir (`crawl/`) is this ticket's own fixture scope, distinct from
sibling `seo1xx/tags/` (T-5374) and `seo1xx/spam/` (T-5365) subdirs,
and from T-5364's own `seo1xx/routes/` substrate fixtures, all under
the same `seo1xx/` parent.

Because no live gate discovers `websec_findings` (see "Discovery
convention" above), this suite has no end-to-end gate-level
positive-control test; the closest equivalent is
`test_websec_findings_emits_violation_when_called_directly`, which
calls the hook directly and asserts on its real `Violation` output.

frob:ticket T-5362
