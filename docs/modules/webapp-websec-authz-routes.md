# frob.webapp._websec_authz_routes -- WEBSEC401-407 route-level authorization

One sentence: `frob.webapp._websec_authz_routes.websec_authz_route_findings`
extends the same taint call site (`frob.gates._taint_gate.taint_gate`)
with a route-level-authorization family -- IDOR/BOLA (reusing T-5356's
`frob.webapp._websec_authz_substrate` walker), admin routes missing an
auth decorator, front-end-only permission guards, mass assignment,
field-level over-exposure, unbounded list-endpoint pagination, and
missing per-user rate limiting -- folded into `taint_gate`'s own scan
rather than a second gate registration (the same reasoning T-5307's
`docs/modules/webapp-websec-injection.md` and every sibling
`docs/modules/webapp-websec-*.md` leaf already documents).

This is a downstream leaf of the T-5140 web-app epic's substrate wave
(docs/modules/webapp.md's own scope: framework detection only, not any
individual rule family).

## Framework gating

`websec_authz_route_findings(root)` calls
`frob.webapp._detect.detect_frameworks` first and returns `()`
immediately for a repo with no detected web framework -- the same
short-circuit every WEBSEC/COMPLY/A11Y/SEO/WEBPERF family uses (T-5302).
This module never re-implements framework sniffing.

## WEBSEC401 reuses T-5356's substrate, it does not re-implement it

`_websec_authz_substrate` (T-5356) is a leaf layer with no `frob.gates`
import of its own: it hands back its own `AuthzFinding` model and
leaves the `frob.lang.raw_tree` parse call to its caller. `frob.webapp`
IS allowed to import `frob.lang` directly (T-5307's `_websec_sinks`
already does this, `[arch.layering]` in `frob.toml`), so this module's
`_idor_bola_findings` is that caller: it parses every tracked `.py`
file with `raw_tree(path, expect_heterogeneous=True)` and every tracked
`.rb` file's raw text, then hands the result to
`scan_python_handlers`/`scan_rails_controller` unchanged.

## Rule catalog

| rule | check | evidence | detection |
| --- | --- | --- | --- |
| WEBSEC401 | an ORM lookup/filter with no correlation to the authenticated user's own identity anywhere in the handler body -- IDOR/BOLA | Python (Flask/FastAPI/Django)/Ruby (Rails) | `_websec_authz_substrate`'s AST/text walker (T-5356), reused unchanged |
| WEBSEC402 | an admin-path route decorator with no framework auth decorator/permission check anywhere in the same file | Python backend | text-regex |
| WEBSEC403 | a React Router admin-path `<Route>` with no wrapping guard component (`Guard`/`Protected`/`Private`/`RequireAuth`) | JSX/TSX frontend | text-regex |
| WEBSEC404 | the whole request body passed to an ORM `create`/`update` call -- mass assignment | Python/JS backend | text-regex |
| WEBSEC405 | a full ORM model serialized whole into a JSON response, no explicit field list -- field-level over-exposure | Python/JS backend | text-regex |
| WEBSEC406 | an ORM `.all()`/`.find()` call with no `limit`/`paginate`/`page`/slice anywhere in the same file -- unbounded list pagination | Python/JS backend | text-regex |
| WEBSEC407 | an auth/expensive-endpoint route (`/login`/`/reset-password`/`/export`) with no rate-limit decorator/call anywhere in the same file | Python backend | text-regex |

WEBSEC401 fills its own id from T-5356's already-landed substrate; this
ticket adds no new detection logic for it, only the `raw_tree`
call-site glue and `Violation` wrapping. All seven reserved ids
(`WEBSEC401`-`WEBSEC407`) are used -- no follow-up ticket for an unused
id this time.

## Known gaps

WEBSEC402/WEBSEC407 are FILE-SCOPE checks, not per-route: a matching
auth/rate-limit decorator anywhere in the same tracked file clears the
finding, even if it does not actually decorate the flagged route -- the
same disclosed granularity gap `_websec_password`'s WEBSEC218/WEBSEC219
checks already carry for a different axis (T-5353). WEBSEC403 is a
text-regex proxy over the SAME file the route table lives in, not a
cross-referenced walk against the server's own route table (the ticket
body's "React router-guard AST cross-referenced against the server
route table" is the full-strength version of this check; this leaf
implements the JSX-local half only -- filed as follow-up scope, see the
T-5357 Done report for the ticket id).

## Severity

WARN-tier at first turn-on -- the same T-0688/T-0973 promotion posture
`taint_gate`/`opaque_gate`/every sibling WEBSEC family already follows
for a brand-new structural rule.

## Public API

- `WebsecAuthzRouteFinding` (`src/frob/webapp/_websec_authz_routes.py`)
  -- one finding: `rule`, `file`, `line`, `message`.
- `websec_authz_route_findings(root: Path) ->
  tuple[WebsecAuthzRouteFinding, ...]` -- every WEBSEC401-407 finding
  under `root`.
- `websec_findings(root: Path, frameworks: frozenset[FrameworkKind]) ->
  tuple[frob.findings.Violation, ...]` -- the `taint_gate` module-
  discovery hook (T-5311): `frob.gates._taint_gate.taint_gate`
  auto-discovers every `frob.webapp._websec_*` module exposing a
  module-level `websec_findings(root, frameworks)` callable and folds
  its returned `Violation`s into the same tuple it returns, so this
  leaf never needs its own hand-edit to `_taint_gate.py`/
  `gates/__init__.py`. `frameworks` is the caller's own
  already-computed `detect_frameworks(root)` result (this hook never
  re-detects); an empty set short-circuits to `()`, same contract as
  `websec_authz_route_findings` itself. `websec_findings` is a thin
  wrapper -- WARN-tier `Violation` construction only, no independent
  detection logic beyond WEBSEC401's substrate call.

## Tests and fixtures

`tests/unit/test_websec_authz_routes.py` -- one positive-control and
one negative-control fixture per rule under
`tests/fixtures/webapp/websec4xx/routes/webesc4{01..07}_{positive,negative}/`,
each carrying a minimal Flask framework marker (`requirements.txt`
naming `flask`, so `detect_frameworks` fires) plus exactly the
route/call shape under test. Positive fixtures plant the gap (an
unfiltered ORM lookup, an admin route with no auth decorator, an
unguarded admin `<Route>`, mass assignment, `jsonify(x.__dict__)`, an
unpaginated `.all()`, a `/login` route with no rate limiter); negative
fixtures use the identical shape with the gap closed, to prove the rule
does not fire on the clean case. This subdir (`routes/`) is this
ticket's own fixture scope, distinct from sibling T-5359's share of
`websec4xx/` (Supabase RLS, webhooks, payments, LLM surface).

frob:ticket T-5357
