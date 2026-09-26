# frob.webapp._websec_logging_limits -- WEBSEC326-334 logging, timeouts, resource limits

One sentence: `frob.webapp._websec_logging_limits.websec_logging_limits_findings`
covers the T-5143 config/headers/supply-chain corpus's auth-event/log-
hygiene and outbound/server/body resource-limit family, auto-discovered
by `frob.gates._taint_gate.taint_gate` via its T-5308 `websec_findings`
hook mechanism rather than a hand-edit to that gate's call site.

This is one of seven sibling web-app-lint story leaves under the T-5140
epic (docs/modules/webapp.md's own scope: framework detection only, not
any individual rule family). A follow-up ticket links all seven family
docs from webapp.md once all seven land.

## Framework gating

`websec_logging_limits_findings(root)` calls
`frob.webapp._detect.detect_frameworks` first and returns `()`
immediately for a repo with no detected web framework -- the same
short-circuit every WEBSEC/COMPLY/A11Y/SEO/WEBPERF family uses (T-5302).
This module never re-implements framework sniffing.

## Rule catalog

| rule | shape | source language | detection |
| --- | --- | --- | --- |
| WEBSEC326 | an auth-event handler (login/logout/authenticate/password-reset name shape) with no logger call anywhere in its body | Python | stdlib `ast` walk over function defs, name-pattern match plus a logger-call regex over the unparsed body |
| WEBSEC327 | a logger call embedding `datetime.now()` (naive local time) instead of a UTC-shaped timestamp | Python | text-regex over the logger-call argument list |
| WEBSEC328 | a logger call whose message embeds a PII field-name-denylist token (ssn, social_security, credit_card, passport, date_of_birth/dob) | Python, TS/JS | text-regex over the logger-call argument list |
| WEBSEC329 | an Express body-parser call with no `limit` key in its options object | TS/JS (`bodyParser.json(...)`/`express.json(...)`) | text-regex over the call-site options object |
| WEBSEC330 | an outbound HTTP client call with no `timeout=` keyword argument | Python (`requests.get/post/put/delete/request(...)`) | text-regex over the call-site argument list |
| WEBSEC331 | a server-start call with no `timeout`/`timeout_keep_alive` keyword argument | Python (`app.run(...)`/`uvicorn.run(...)`) | text-regex over the call-site argument list |
| WEBSEC332 | a GraphQL server construction with no introspection/depth-limit reference anywhere in the same file | TS/JS (`ApolloServer(...)`/`GraphQLView.as_view(...)`/`graphene.Schema(...)`) | text-regex over the construction call plus a whole-file guard-token search |
| WEBSEC333 | a debug/test route path literal, or `debug=True` on a server-start call | Python, TS/JS | text-regex over route-decorator/call-site string literals and server-start keyword arguments |
| WEBSEC334 | a logout/signOut handler function with no `localStorage`/`sessionStorage` clear/removeItem call anywhere in its body | TS/JS | brace-matched function-body extraction plus a storage-clear-call regex |

Each fires only on a bound-bearing shape (an auth-event-named function, a
logger call, a body-parser/HTTP-client/server-start call, a GraphQL
server construction, a route registration, or a logout handler) -- this
is intra-statement/intra-function text and structure, not resolved
cross-file data-flow, the same disclosed gap SEC005 (T-0781) and
WEBSEC101-106 (T-5307) already carry.

## Deferred corpus items

Two ticket-body corpus items -- log-retention policy and an outbound
egress allowlist, both pure config-posture checks with no single
reliable static shape across frameworks (retention/allowlist config
lives in wildly different places per stack: environment variables, a
cloud provider console, an infra-as-code file this repo's own tracked
tree may not even contain) -- have no id left in this leaf's nine-id
`WEBSEC326`-`WEBSEC334` reservation and are not implemented here. They
are filed as follow-up scope in this leaf's Done report rather than
shipped as an unreliable, high-false-positive-risk guess.

The WebSocket origin-check/WSS-enforcement item from the ticket body's
corpus stays owned by `frob.webapp._websec_headers_log.
websec_headers_log_findings` (`WEBSEC122`, T-5141-4) -- this module
never reimplements it, and cross-references that rule id instead.

## Severity

WARN-tier at first turn-on -- the same T-0688/T-0973 promotion posture
every sibling WEBSEC family follows: a real fix-or-waive pass over the
first measured hit set decides whether ERROR is safe later.

## Public API

- `WebsecLoggingLimitsFinding` (`src/frob/webapp/_websec_logging_limits.py`)
  -- one finding: `rule`, `file`, `line`, `message`.
- `websec_logging_limits_findings(root: Path) ->
  tuple[WebsecLoggingLimitsFinding, ...]` -- every WEBSEC326-334 finding
  under `root`.
- `websec_findings(root: Path, frameworks: frozenset[FrameworkKind]) ->
  tuple[Violation, ...]` -- the T-5308 `taint_gate` discovery hook;
  `frameworks` is the caller's own already-computed
  `detect_frameworks(root)` result.

`frob.gates._taint_gate.taint_gate` discovers `websec_findings` via
`pkgutil.iter_modules` over `frob.webapp` and folds the results into the
same `Violation` tuple it returns -- there is no separate
`websec_logging_limits_gate` process job and no hand-edit to
`_taint_gate.py`.

## Tests and fixtures

`tests/unit/test_websec_logging_limits.py` -- one positive-control and
one negative-control fixture per rule under
`tests/fixtures/webapp/websec3xx/logging/websec32{6..9}_{positive,negative}/`
and `websec33{0..4}_{positive,negative}/`, each carrying a `manage.py`
framework marker (`import django`, so `detect_frameworks` fires) plus
exactly one rule-bearing occurrence. Positive fixtures plant the
unguarded shape; negative fixtures use the identical shape with the
guard/limit/timeout/logger call present, to prove the rule does not
fire on the clean case.
`test_taint_gate_discovers_websec_logging_limits_hook` is the positive
control proving the T-5308 discovery mechanism finds this module's hook
end to end through a real git repo, with no hard-coded
`_taint_gate.py` call site for this rule family.

frob:ticket T-5332
