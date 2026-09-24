# frob.webapp._websec_headers_rules -- WEBSEC301-309 config/headers rules

One sentence: `websec_headers_rules_findings` maps
`frob.webapp._websec_headers.lint_response_headers`'s per-header
evidence onto nine concrete WEBSEC rule ids (301-309), adding its own
value-level checks (HSTS `max-age`, CSP nonce) and its own tiny
tracked-file text scans for the headers/concerns the T-5325 substrate
does not itself cover (Permissions-Policy, COOP/COEP/CORP, CORS,
Cache-Control-on-authenticated-responses).

## Relationship to `frob.webapp._websec_headers` (T-5325)

`_websec_headers.py` is the response-header EVIDENCE engine
(`docs/modules/webapp-websec-headers.md`); its `lint_response_headers`
carries a `frob:waive WIRE001` naming this ticket (T-5326) as the module
that wires its `HeaderFinding`s onto gate rule ids. This module is that
wiring for `Strict-Transport-Security`, `Content-Security-Policy`,
`X-Content-Type-Options`, and `Referrer-Policy` (WEBSEC301-304); it never
re-implements the nginx/Caddy/Django/helmet parsing that engine already
owns, it only calls `lint_response_headers` and reads `HeaderStatus`.

`Permissions-Policy` (WEBSEC305), COOP/COEP/CORP (WEBSEC306), CORS
(WEBSEC307/308), and Cache-Control-on-authenticated-responses (WEBSEC309)
are NOT in the substrate's `REQUIRED_HEADERS`, so this module keeps its
own small tracked-file text scans for those -- the same "own tiny
private copy, not a cross-module private import" posture
`_websec_headers_log.py`'s module docstring documents.

## The nine rule ids

- **WEBSEC301** -- HSTS `max-age >= 31536000` (ASVS 5.0 V3.4.1/V3.7.4).
  Wraps the substrate's `Strict-Transport-Security` finding; PRESENT
  additionally requires a `max-age=` value at or above the one-year
  floor, read directly from the evidence file.
- **WEBSEC302** -- CSP with a `nonce-` fragment (V3.4.3). Wraps the
  substrate's `Content-Security-Policy` finding; PRESENT additionally
  requires a `nonce-` fragment in the evidence file.
- **WEBSEC303** -- `X-Content-Type-Options: nosniff` (V3.4.4). Direct
  passthrough of the substrate's finding.
- **WEBSEC304** -- `Referrer-Policy` (V3.4.5). Direct passthrough of the
  substrate's finding.
- **WEBSEC305** -- `Permissions-Policy`. Fires when no tracked
  nginx/Caddy config or app file under the repo mentions the header name
  at all.
- **WEBSEC306** -- COOP/COEP/CORP. Fires when no tracked file mentions
  any of `Cross-Origin-Opener-Policy`, `Cross-Origin-Embedder-Policy`, or
  `Cross-Origin-Resource-Policy`.
- **WEBSEC307** -- CORS wildcard origin (V3.4.2). Fires on
  `Access-Control-Allow-Origin: *` anywhere in a tracked file (ASVS wants
  a fixed/allowlisted origin instead).
- **WEBSEC308** -- CORS-preflight reliance for sensitive functionality
  (V3.5.1/V3.5.2). A proxy heuristic, not a full request-authz trace:
  fires when a wildcard `Access-Control-Allow-Origin` co-occurs with
  `Access-Control-Allow-Credentials: true` in the same file.
- **WEBSEC309** -- `Cache-Control: no-store` on authenticated responses
  (V14.3.2). This module is the canonical owner of this rule id
  (T-5147-6/WEBPERF server-network blocks on this leaf rather than
  reimplementing authenticated-route detection). A proxy heuristic:
  fires when a file references an authenticated-route marker
  (`login_required`, `request.user`, `req.session`, `jwt_required`) with
  no `Cache-Control`/`no-store` anywhere in the same file.

## Public API

### WebsecHeaderRuleFinding

`@dataclass(frozen=True)`: `rule: str`, `file: str`, `line: int`,
`message: str` -- one WEBSEC301-309 finding.

### websec_headers_rules_findings

`websec_headers_rules_findings(root: Path) -> tuple[WebsecHeaderRuleFinding, ...]`

Short-circuits to `()` when `frob.webapp._detect.detect_frameworks(root)`
reports no web framework at all (T-5302's contract, same posture every
sibling WEBSEC family follows).

### websec_findings

`websec_findings(root: Path, frameworks: frozenset[FrameworkKind]) -> tuple[Violation, ...]`

`frob.gates._taint_gate.taint_gate`'s pkgutil-discovery hook (T-5311):
any `frob.webapp._websec_*` module exposing this exact signature is
auto-folded into the gate's scan, so this leaf needed no
`_taint_gate.py` edit. WARN-tier at first turn-on (T-0688/T-0973
promotion posture).

## Fixtures

`tests/fixtures/webapp/websec3xx/headers/` -- one positive and one
negative directory per rule id (`websec301_positive`/
`websec301_negative`, ... `websec309_positive`/`websec309_negative`),
each carrying a `requirements.txt` naming `flask` so `detect_frameworks`
reports `FrameworkKind.FLASK` and the scan runs. These are separate from
T-5325's own top-level `tests/fixtures/webapp/websec3xx/` fixtures
(`nginx_full`, `caddy_full`, ...), which remain that ticket's scope.
