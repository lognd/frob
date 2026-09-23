# frob.webapp._websec_headers_log -- WEBSEC117-122 header/URL/log injection and WebSocket origin enforcement

One sentence: `frob.webapp._websec_headers_log.websec_headers_log_findings`
extends the same SEC005/WEBSEC101-106 taint call site
(`frob.gates._taint_gate.taint_gate`) with a THIRD framework-scoped
source/sink family covering response-header/URL/log injection and
WebSocket origin/WSS enforcement (ASVS 5.0 V4.4.1/V4.4.2, V7.2,
V13.2.1-shaped; CWE-113/CWE-117), folded into `taint_gate`'s own scan
rather than a second gate registration -- the same reasoning T-5307's
`docs/modules/webapp-websec-injection.md` already documents for
WEBSEC101-106.

This is a downstream leaf of the T-5140 web-app epic's seven-sibling
substrate wave (docs/modules/webapp.md's own scope: framework detection
only, not any individual rule family). A follow-up ticket links this doc
(plus session/CSRF, response headers, authz, COMPLY, A11Y, SEO/WEBPERF)
from webapp.md.

## Framework gating

`websec_headers_log_findings(root)` calls
`frob.webapp._detect.detect_frameworks` first and returns `()`
immediately for a repo with no detected web framework -- the same
short-circuit every WEBSEC/COMPLY/A11Y/SEO/WEBPERF family uses (T-5302).
This module never re-implements framework sniffing.

## Rule catalog

| rule | sink | source language | detection |
| --- | --- | --- | --- |
| WEBSEC117 | `response.setHeader(...)`/`res.setHeader(...)`/`.headers[...] = ...` assigned a request-derived value | Python/JS backend | text-regex |
| WEBSEC118 | a URL string built by concatenating/f-string-interpolating request-derived data | Python/JS backend | text-regex |
| WEBSEC119 | a `logger.*(...)` call whose message embeds request-derived data | Python backend | text-regex |
| WEBSEC120 | `Content-Disposition`/filename header built from a request-derived value | Python/JS backend | text-regex |
| WEBSEC121 | `requests.get/post/request(<request-derived url>, ...)` with `allow_redirects` left at its default `True` | Python backend | text-regex |
| WEBSEC122 | `new WebSocket("ws://...")` (insecure scheme), or a WebSocket handler file with no `origin` reference anywhere | JS frontend / any backend | text-regex |

Each fires only when the flagged expression references a request-derived
source (`request.args/form/values/GET/POST/headers/json/data/
query_params`, or the generic `req.params/query/body/headers` accessor
shape) and has NOT already passed through a recognized encode/sanitize
call (`urlencode`, `quote`, `shlex.quote`, `repr(...)`, `%r`, `sanitize`,
`escape`, or an explicit CR/LF `.replace(...)` call) on the SAME matched
line -- intra-line, not resolved data-flow, the same disclosed gap
T-5307's `websec_sink_findings`/SEC005 (T-0781) already carry.
WEBSEC122's two checks are independent: an insecure `ws://` literal is
its own finding regardless of origin-check presence, and a WebSocket
handler file with zero `origin` references anywhere is a second,
separate finding.

WEBSEC117-122's fuller ticket-body corpus (HTML injection in
transactional email, field over-exposure via `jsonify(model.__dict__)`
whole-object serialization) has no rule id left in this six-id
reservation (`WEBSEC117`-`WEBSEC122`, T-5301) and is deliberately left
unimplemented here -- filed as follow-up scope (see the T-5308 Done
report for the ticket id).

## Severity

WARN-tier at first turn-on -- the same T-0688/T-0973 promotion posture
`taint_gate`/`opaque_gate`/T-5307's `websec_sink_findings` already follow
for a brand-new structural rule: a real fix-or-waive pass over the first
measured hit set decides whether ERROR is safe later.

## Public API

- `WebsecHeaderLogFinding` (`src/frob/webapp/_websec_headers_log.py`) --
  one finding: `rule`, `file`, `line`, `message`.
- `websec_headers_log_findings(root: Path) -> tuple[WebsecHeaderLogFinding, ...]`
  -- every WEBSEC117-122 finding under `root`.
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
  `websec_headers_log_findings` itself. `websec_findings` is a thin
  wrapper over `websec_headers_log_findings` -- WARN-tier `Violation`
  construction only, no independent detection logic.

## Tests and fixtures

`tests/unit/test_websec_headers_log.py` -- one positive-control and one
negative-control fixture per rule under
`tests/fixtures/webapp/websec1xx/headers_log/websec1{17..22}_{positive,negative}/`,
each carrying a minimal Django framework marker (`manage.py` with
`import django`, so `detect_frameworks` fires) plus exactly the sink
shape under test. Positive fixtures plant a request-derived,
unencoded/unsanitized value; negative fixtures use the identical sink
shape with an encoded/sanitized value (or, for WEBSEC121, an explicit
`allow_redirects=False`; for WEBSEC122, a `wss://` scheme plus an
`origin` check), to prove the rule does not fire on the clean case.

frob:ticket T-5308
