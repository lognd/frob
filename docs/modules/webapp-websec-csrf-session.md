# frob.webapp._websec_csrf_session -- WEBSEC201-208 CSRF and session lifecycle

One sentence: `frob.webapp._websec_csrf_session.websec_csrf_session_findings`
extends `frob.gates._taint_gate.taint_gate`'s WEBSEC scan with a NINTH
framework-scoped family covering CSRF wiring, session-cookie hardening,
session lifetime, and session-id lifecycle (rotation/invalidation),
folded into `taint_gate`'s own scan via T-5308's pkgutil-discovery hook
rather than a second gate registration -- the same reasoning T-5307's
`docs/modules/webapp-websec-injection.md` already documents for
WEBSEC101-106.

This is a downstream leaf of the T-5140 web-app epic's seven-sibling
substrate wave (`docs/modules/webapp.md`'s own scope: framework
detection only, not any individual rule family), and specifically
downstream of T-5349's normalized session-config reader
(`frob.webapp._websec_session_config.read_session_config`).

## Framework gating

`websec_csrf_session_findings(root)` calls
`frob.webapp._detect.detect_frameworks` first and returns `()`
immediately for a repo with no detected web framework -- the same
short-circuit every WEBSEC/COMPLY/A11Y/SEO/WEBPERF family uses (T-5302).
This module never re-implements framework sniffing.

## Rule catalog

Split exactly the way the ticket body splits them: four "handler-shape"
rules read a route/controller file's own text; four "config" rules read
T-5349's `SessionConfig` instead of re-parsing the framework's session
config file.

| rule | shape | source |
| --- | --- | --- |
| WEBSEC201 | a GET-only route whose handler window calls a write-shaped method/verb (`.save(`/`.delete(`/`.destroy(`/`.update(`/`.create(`/an SQL DML keyword) | handler-shape, text-window scan |
| WEBSEC204 | a client-supplied cookie/header value compared directly, with no server-side session-store/DB lookup call anywhere in the file | handler-shape, text scan |
| WEBSEC205 | a login-shaped handler sets session authentication state but the file has no session-rotation call anywhere | handler-shape, text scan |
| WEBSEC208 | a logout-shaped handler exists but the file has no session-invalidation call anywhere | handler-shape, text scan |
| WEBSEC202 | `SessionConfig.csrf_middleware_present` is `False` | config, `read_session_config` |
| WEBSEC203 | `SessionConfig.samesite` is `None` or `"none"` (case-insensitive) | config, `read_session_config` |
| WEBSEC206 | `SessionConfig.idle_timeout` is `None` | config, `read_session_config` |
| WEBSEC207 | `SessionConfig.absolute_timeout` is `None` | config, `read_session_config` |

WEBSEC201's GET-route detection and WEBSEC204/205/208's handler-shape
detection are TEXT-REGEX/text-window scans, the same disclosed-gap
"textual proxy, not resolved data-flow" posture every text-regex WEBSEC
family in this epic carries -- WEBSEC201 in particular looks for a
write-shaped call within a fixed character window after the matched
route line, not a real route-handler-body isolation (no brace/indent
matching). WEBSEC202/203/206/207 read T-5349's `SessionConfig` directly
and never re-parse the framework's config file themselves; only
frameworks with a `read_session_config` reader registered (Django,
Flask, Rails, and Node/Express detected as `FrameworkKind.VITE`)
contribute config findings -- FastAPI/Laravel/SvelteKit/Astro/Next.js
contribute none (T-5349's own `UnsupportedFramework` posture).

### Deliberately out of scope: account-enumeration-via-error-text

The ticket body's fuller corpus includes "the static half of
account-enumeration-via-error-text" (distinguishable login/signup error
messages leaking whether an account exists). No rule id is left in the
`WEBSEC201`-`WEBSEC208` eight-id reservation (T-5301) for it -- it is
deliberately NOT implemented here, filed as follow-up scope instead (see
the T-5351 Done report for the ticket id), the same posture
`_websec_headers_log.py`/`_websec_xss.py` already document for their own
fuller ticket-body corpora.

## Severity

WARN-tier at first turn-on -- the same T-0688/T-0973 promotion posture
`taint_gate`/every other WEBSEC family in this epic already follows for
a brand-new structural rule.

## Public API

- `WebsecCsrfSessionFinding` (`src/frob/webapp/_websec_csrf_session.py`)
  -- one finding: `rule`, `file`, `line`, `message`.
- `websec_csrf_session_findings(root: Path) ->
  tuple[WebsecCsrfSessionFinding, ...]` -- every WEBSEC201-208 finding
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
  `websec_csrf_session_findings` itself.

## Tests and fixtures

`tests/unit/test_websec_csrf_session.py` -- one positive-control and one
negative-control fixture per rule under
`tests/fixtures/webapp/websec2xx/csrf_session/webesc2{01..08}_{positive,negative}/`,
each carrying a minimal Flask (`requirements.txt` with `flask`) or
Django (`manage.py`/`settings.py`) framework marker so
`detect_frameworks` fires, plus exactly the handler/config shape under
test. WEBSEC206/207's fixtures deliberately pick the one framework whose
reader always leaves that field `None` regardless of file content
(Django never sets `idle_timeout`, Flask/Express/Rails never set
`absolute_timeout`) for the positive case, and the framework whose
reader can state it for the negative case. Also includes an end-to-end
positive control (`test_taint_gate_discovers_websec_csrf_session_hook`)
proving `frob.gates._taint_gate.taint_gate` discovers and calls this
module's hook with no `_taint_gate.py` edit.

frob:ticket T-5351
