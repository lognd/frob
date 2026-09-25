# frob.webapp._websec_tokens -- WEBSEC209-216 JWT and OAuth token checks

One sentence: `frob.webapp._websec_tokens.websec_token_findings` extends
the same taint call site (`frob.gates._taint_gate.taint_gate`) with a
JWT/OAuth-token family -- validation gaps at a `jwt.decode`/
`jwt.verify` call site, and authorization-code-flow config/URL
weaknesses -- folded into `taint_gate`'s own scan rather than a second
gate registration (the same reasoning T-5307's
`docs/modules/webapp-websec-injection.md`, T-5308's
`docs/modules/webapp-websec-headers-log.md`, and T-5329's
`docs/modules/webapp-websec-debug-config.md` already document).

This is a downstream leaf of the T-5140 web-app epic's substrate wave
(docs/modules/webapp.md's own scope: framework detection only, not any
individual rule family).

## Framework gating

`websec_token_findings(root)` calls `frob.webapp._detect.detect_frameworks`
first and returns `()` immediately for a repo with no detected web
framework -- the same short-circuit every WEBSEC/COMPLY/A11Y/SEO/WEBPERF
family uses (T-5302). This module never re-implements framework
sniffing.

## Rule catalog

| rule | check | evidence | detection |
| --- | --- | --- | --- |
| WEBSEC209 | `jwt.decode`/`jwt.verify` explicitly disables exp/nbf validation | Python/JS backend call site | text-regex |
| WEBSEC210 | `jwt.decode`/`jwt.verify` with no `audience`/`aud` argument | Python/JS backend call site | text-regex |
| WEBSEC211 | `jwt.decode`/`jwt.verify` with no `issuer`/`iss` argument | Python/JS backend call site | text-regex |
| WEBSEC212 | Django REST Framework SimpleJWT `SIMPLE_JWT` config: rotation disabled or no absolute `REFRESH_TOKEN_LIFETIME` | Python backend config | text-regex |
| WEBSEC213 | a token spliced into a URL query string or fragment | Python/JS backend | text-regex |
| WEBSEC214 | an OAuth authorization-request URL built with no `state=` parameter | Python/JS backend | text-regex |
| WEBSEC215 | an OAuth client config with a wildcard/prefix-shaped `redirect_uri` | Python/JS/JSON config | text-regex |
| WEBSEC216 | an OAuth authorization-code request (`response_type=code`) with no `code_challenge=` parameter (PKCE) | Python/JS backend | text-regex |

`WEBSEC217` is reserved but unimplemented in this leaf -- the ticket
body's default-credential/secrets-committed item is SEC001-003's job
(cross-referenced, not duplicated here) and consumed no id; the ninth
reserved id is follow-up scope, see the T-5352 Done report for the
ticket id.

The ticket body's own "AST lint on jwt.decode/jsonwebtoken.verify
call-argument presence" is approximated as a call-site text-regex over
the matched parenthesized argument list here, the same idiom
`_websec_headers_log`/`_websec_debug_config` already use for JS/TS
evidence (`frob.lang`'s identifier walker has no javascript/typescript
entry yet, T-3232).

## Severity

WARN-tier at first turn-on -- the same T-0688/T-0973 promotion posture
`taint_gate`/`opaque_gate`/every sibling WEBSEC family already follows
for a brand-new structural rule.

## Public API

- `WebsecTokenFinding` (`src/frob/webapp/_websec_tokens.py`) -- one
  finding: `rule`, `file`, `line`, `message`.
- `websec_token_findings(root: Path) -> tuple[WebsecTokenFinding, ...]`
  -- every WEBSEC209-216 finding under `root`.
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
  `websec_token_findings` itself. `websec_findings` is a thin wrapper
  -- WARN-tier `Violation` construction only, no independent detection
  logic.

## Tests and fixtures

`tests/unit/test_websec_tokens.py` -- one positive-control and one
negative-control fixture per rule under
`tests/fixtures/webapp/websec2xx/jwt_oauth/webesc2{09..16}_{positive,negative}/`,
each carrying a minimal Django framework marker (`manage.py` with
`import django`, so `detect_frameworks` fires) plus exactly the
call-argument or config shape under test. Positive fixtures plant the
gap (`verify_exp: False`, a missing `audience`/`issuer` keyword, a
disabled/unbounded `SIMPLE_JWT` config, a token spliced into a URL, an
OAuth URL missing `state=`/`code_challenge=`, a wildcard
`redirect_uri`); negative fixtures use the identical shape with the gap
closed, to prove the rule does not fire on the clean case. This subdir
(`jwt_oauth/`) is this ticket's own fixture scope, distinct from the
sibling `csrf_session/` subdir T-5351's session/CSRF leaf owns under
the same `websec2xx/` parent.

frob:ticket T-5352
