# frob.webapp._websec_random_tls -- WEBSEC226-230 randomness and TLS verification

One sentence: `frob.webapp._websec_random_tls.websec_random_tls_findings`
extends `frob.gates._taint_gate.taint_gate`'s WEBSEC scan with a rule
family covering insecure randomness for security-sensitive values, TLS
verification/configuration, mobile certificate pinning, and
credential-stuffing rate-limiting, folded into `taint_gate`'s own scan
via T-5308's pkgutil-discovery hook rather than a second gate
registration -- the same reasoning T-5307's
`docs/modules/webapp-websec-injection.md` already documents for
WEBSEC101-106.

This is a downstream leaf of the T-5140 web-app epic's seven-sibling
substrate wave (`docs/modules/webapp.md`'s own scope: framework
detection only, not any individual rule family).

## Framework gating

`websec_random_tls_findings(root)` calls
`frob.webapp._detect.detect_frameworks` first and returns `()`
immediately for a repo with no detected web framework -- the same
short-circuit every WEBSEC/COMPLY/A11Y/SEO/WEBPERF family uses (T-5302).
This module never re-implements framework sniffing.

## Rule catalog

All five rules are TEXT-REGEX/text-window scans, the same disclosed-gap
"textual proxy, not resolved data-flow" posture every text-regex WEBSEC
family in this epic carries.

| rule | shape | detection |
| --- | --- | --- |
| WEBSEC226 | `random.random()`/`random.randint(`/`Math.random()` assigned to a variable whose name looks like a token/session-id/API-key/CSRF-token | name-based heuristic on the assignment target |
| WEBSEC227 | `verify=False`/`rejectUnauthorized: false`, or a literal `http://` URL passed straight to an outbound API call | text-regex |
| WEBSEC228 | an `SSLContext(`/`wrap_socket(`/`createServer(` call with no minimum-TLS-version keyword in the following text window | text-window scan |
| WEBSEC229 | a mobile HTTP client indicator (`URLSession(`/`AFHTTPSessionManager`/`OkHttpClient`) with no pinning-library keyword anywhere in the tracked mobile source | tracked-file-set text scan |
| WEBSEC230 | a login-shaped handler with no rate-limit indicator anywhere in the same file | text scan |

### WEBSEC229 is advisory and monorepo-scoped

WEBSEC229 (certificate pinning) is explicitly a mobile-app concern, but
`frob.webapp._detect.detect_frameworks` only recognizes web frameworks
-- it never detects a mobile app on its own. Since T-5302's framework
gate applies to the whole file set (not per-file), this rule only ever
fires in the specific shape of a monorepo that mixes a detected web
framework (so the gate opens) with `.swift`/`.m`/`.java`/`.kt` mobile
client source. This is a deliberate, documented narrowing, not a
silently missed case: a pure mobile-app repo (no web framework detected
anywhere) never reaches this scan at all.

### WEBSEC230 cross-references T-5144-2

WEBSEC230 (credential-stuffing rate-limit) detects the ABSENCE of a
rate-limit indicator near a login handler; it does not reimplement
T-5144-2's own generic rate-limit rule, only cross-references it.

### Deliberately out of scope: HSTS

HSTS enforcement is owned by T-5143-2's response-header-lint substrate
(the WEBSEC3xx family, `frob.webapp._websec_headers`); this leaf blocks
on that substrate rather than reimplementing header parsing.

## Severity

WARN-tier at first turn-on -- the same T-0688/T-0973 promotion posture
`taint_gate`/every other WEBSEC family in this epic already follows for
a brand-new structural rule.

## Public API

- `WebsecRandomTlsFinding` (`src/frob/webapp/_websec_random_tls.py`) --
  one finding: `rule`, `file`, `line`, `message`.
- `websec_random_tls_findings(root: Path) ->
  tuple[WebsecRandomTlsFinding, ...]` -- every WEBSEC226-230 finding
  under `root`.
- `websec_findings(root: Path, frameworks: frozenset[FrameworkKind]) ->
  tuple[frob.findings.Violation, ...]` -- the `taint_gate` module-
  discovery hook (T-5308): `frob.gates._taint_gate.taint_gate`
  auto-discovers every `frob.webapp._websec_*` module exposing a
  module-level `websec_findings(root, frameworks)` callable and folds
  its returned `Violation`s into the same tuple it returns, so this
  leaf never needs its own hand-edit to `_taint_gate.py`/
  `gates/__init__.py`. `frameworks` is the caller's own
  already-computed `detect_frameworks(root)` result (this hook never
  re-detects); an empty set short-circuits to `()`, same contract as
  `websec_random_tls_findings` itself.

## Tests and fixtures

`tests/unit/test_websec_random_tls.py` -- one positive-control and one
negative-control fixture per rule under
`tests/fixtures/webapp/websec2xx/random_tls/webesc2{26..30}_{positive,negative}/`,
each carrying a minimal Flask (`requirements.txt` with `flask`)
framework marker so `detect_frameworks` fires, plus exactly the
randomness/TLS/handler shape under test (WEBSEC229's fixtures also
carry a `.swift` mobile-client file alongside the Flask marker, the
monorepo shape this rule requires to fire at all). Also includes an
end-to-end positive control
(`test_taint_gate_discovers_websec_random_tls_hook`) proving
`frob.gates._taint_gate.taint_gate` discovers and calls this module's
hook with no `_taint_gate.py` edit.

frob:ticket T-5354
