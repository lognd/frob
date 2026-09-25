# frob.webapp._webperf_server -- WEBPERF109-115 server/network performance config

One sentence: `frob.webapp._webperf_server.webperf_server_findings`
checks response compression, general caching headers, HTTP/2, next-gen
image format offering, CDN cache hints, a server-side cache layer over
expensive queries, and two React render-performance lint shapes
(undebounced input handlers, `useEffect` calls with no dependency
array) -- all TEXT-REGEX over nginx/Caddy/Express/Flask config and
tracked source, the same config-scanning idiom
`frob.webapp._websec_headers.lint_response_headers` (T-5325) already
established for this repo.

This is a downstream leaf of the T-5140 web-app epic's substrate wave
(docs/modules/webapp.md's own scope: framework detection only, not any
individual rule family).

## Framework gating

`webperf_server_findings(root)` calls
`frob.webapp._detect.detect_frameworks` first and returns `()`
immediately for a repo with no detected web framework -- the same
short-circuit every WEBSEC/COMPLY/A11Y/SEO/WEBPERF family uses (T-5302).

## Discovery convention

Same posture the sibling SEO leaves (tags/spam/crawl -- T-5374/T-5365/
T-5362) document in full for their own doc pages:
`docs/modules/webapp-seo.md` defines no leaf-hook convention, and
`frob.gates._taint_gate`'s pkgutil discovery only scans
`frob.webapp._websec_*`-prefixed modules -- `_webperf_server` does not
match, so this module's `websec_findings` hook is not currently
auto-discovered by any live gate either.

T-draft-553232aa is the actual fix: T-5372 already generalized
`_taint_gate`'s discovered-module-prefix tuple to `("_websec_",
"_comply_")`, and per the coordinator's plan T-draft-553232aa widens
that same tuple to also include `"_seo_"`/`"_webperf_"` plus one
end-to-end control per family. Once it lands, this module's
`websec_findings` hook is discovered for free.

## Rule catalog

| rule | check | detection |
| --- | --- | --- |
| WEBPERF109 | no compression middleware/config found anywhere across nginx.conf/Caddyfile/app.js/app.py (repo-wide aggregate) | text-regex |
| WEBPERF110 | an nginx/Caddy config with no `Cache-Control` directive anywhere | text-regex |
| WEBPERF111 | an nginx config with TLS enabled but no `http2` keyword anywhere | text-regex |
| WEBPERF112 | an `<img>` referencing a `.jpg`/`.png` source with no `.webp`/`.avif` offered anywhere in the file | text-regex |
| WEBPERF113 | a static-asset nginx `location` block with no `public`/`immutable` Cache-Control value | text-regex |
| WEBPERF114 | an ORM query call in a Python file with no caching call/decorator anywhere in that file | text-regex |
| WEBPERF115 | a JSX/TSX `onChange={...}` with no `debounce` reference anywhere in the file, or a `useEffect(` with no dependency-array argument | text-regex |

All seven reserved ids (`WEBPERF109`-`WEBPERF115`) are used.

Cache-Control-on-hashed-assets is T-5143-2's job, pagination-on-list-
endpoints is T-5144-2's (also the route-level authorization leaf's own
WEBSEC406, T-5357 -- lands separately), and DB-pool-config is
T-5148-4's -- this leaf blocks on all three (`blocked_by=['T-5364']`
in the ticket ledger, plus the ticket body's own cross-references) and
never re-implements any of them.

WEBPERF109/WEBPERF114/WEBPERF115 are FILE-SCOPE (WEBPERF109 is
REPO-WIDE) checks, not per-call-site: a matching hint anywhere in the
scanned file(s) clears the finding, even if it does not actually cover
the flagged call path -- the same disclosed granularity gap
`_websec_password`'s WEBSEC218/WEBSEC219 checks and
`_websec_authz_routes`'s WEBSEC402/WEBSEC407 checks already carry for
the same reason (T-5353/T-5357).

## Severity

WARN-tier at first turn-on -- the same T-0688/T-0973 promotion posture
`taint_gate`/`opaque_gate`/every sibling WEBSEC/SEO/WEBPERF family
already follows for a brand-new structural rule.

## Public API

- `WebsecWebperfServerFinding` (`src/frob/webapp/_webperf_server.py`)
  -- one finding: `rule`, `file`, `line`, `message`.
- `webperf_server_findings(root: Path) ->
  tuple[WebsecWebperfServerFinding, ...]` -- every WEBPERF109-115
  finding under `root`.
- `websec_findings(root: Path, frameworks: frozenset[FrameworkKind]) ->
  tuple[frob.findings.Violation, ...]` -- see "Discovery convention"
  above; a thin `Violation`-wrapping caller over
  `webperf_server_findings`, not currently reachable through any live
  gate.

## Tests and fixtures

`tests/unit/test_webperf_server.py` -- one positive-control and one
negative-control fixture per rule under
`tests/fixtures/webapp/webperf1xx/server/webperf1{09..15}_{positive,negative}/`,
each carrying a minimal Flask framework marker (`requirements.txt`
naming `flask`, so `detect_frameworks` fires) plus exactly the
config/source shape under test. This subdir (`server/`) is this
ticket's own fixture scope, distinct from sibling
`webperf1xx/markup/**` (T-5371, another agent, in progress; not
touched).

Because no live gate discovers `websec_findings` (see "Discovery
convention" above), this suite has no end-to-end gate-level
positive-control test; the closest equivalent is
`test_websec_findings_emits_violation_when_called_directly`, which
calls the hook directly and asserts on its real `Violation` output.

frob:ticket T-5366
