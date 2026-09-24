# frob.webapp._websec_debug_config -- WEBSEC310-316 debug/info-leak configuration

One sentence: `frob.webapp._websec_debug_config.websec_debug_config_findings`
extends the same taint call site (`frob.gates._taint_gate.taint_gate`)
with a debug/info-leak-configuration family -- production-facing
configuration and build artifacts that disclose internal state or source
to an attacker -- folded into `taint_gate`'s own scan rather than a
second gate registration (the same reasoning T-5307's
`docs/modules/webapp-websec-injection.md` and T-5308's
`docs/modules/webapp-websec-headers-log.md` already document).

This is a downstream leaf of the T-5140 web-app epic's substrate wave
(docs/modules/webapp.md's own scope: framework detection only, not any
individual rule family).

## Framework gating

`websec_debug_config_findings(root)` calls
`frob.webapp._detect.detect_frameworks` first and returns `()`
immediately for a repo with no detected web framework -- the same
short-circuit every WEBSEC/COMPLY/A11Y/SEO/WEBPERF family uses (T-5302).
This module never re-implements framework sniffing.

## Rule catalog

| rule | check | evidence | detection |
| --- | --- | --- | --- |
| WEBSEC310 | Django `DEBUG = True` left as a literal (not env-derived) in `settings.py` | Python backend config | text-regex |
| WEBSEC311 | a webpack/vite config setting `devtool: 'source-map'`, or a tracked `.js.map`/`.css.map` file under a build-output directory | JS build config / tracked build output | text-regex |
| WEBSEC312 | Flask `app.run(debug=True)`/`app.config['DEBUG'] = True`, or an Express error handler sending `err.stack` in the response | Python/JS backend | text-regex |
| WEBSEC313 | nginx `autoindex on;` or Apache `Options +Indexes` | reverse-proxy/web-server config | text-regex |
| WEBSEC314 | a Dockerfile `COPY . .`-shaped broad copy with no sibling `.dockerignore` excluding `.git` | deploy-pipeline config | text-regex |
| WEBSEC315 | Terraform/CloudFormation IaC text containing a `public-read`/`AllUsers`-shaped ACL grant | IaC | text-regex |
| WEBSEC316 | a hardcoded-looking `api_key`/`secret`/`token`/`password` string literal in a tracked front-end bundle | tracked build output | text-regex |

`WEBSEC317` is reserved but unimplemented in this leaf -- the ticket
body's default-credential item is SEC001-003's job (cross-referenced,
not duplicated here) and consumed no id; the eighth reserved id is
follow-up scope, see the T-5329 Done report for the ticket id.

WEBSEC316 uses a small self-contained pattern table local to this
module rather than reusing T-5141's secret-pattern table, since that
ticket's module has not landed yet -- folding WEBSEC316 onto it once it
exists is filed as follow-up scope (T-5329 Done report).

## Severity

WARN-tier at first turn-on -- the same T-0688/T-0973 promotion posture
`taint_gate`/`opaque_gate`/every sibling WEBSEC family already follows
for a brand-new structural rule.

## Public API

- `WebsecDebugConfigFinding` (`src/frob/webapp/_websec_debug_config.py`)
  -- one finding: `rule`, `file`, `line`, `message`.
- `websec_debug_config_findings(root: Path) ->
  tuple[WebsecDebugConfigFinding, ...]` -- every WEBSEC310-316 finding
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
  `websec_debug_config_findings` itself. `websec_findings` is a thin
  wrapper -- WARN-tier `Violation` construction only, no independent
  detection logic.

## Tests and fixtures

`tests/unit/test_websec_debug_config.py` -- one positive-control and
one negative-control fixture per rule under
`tests/fixtures/webapp/websec3xx/debug/webesc3{10..16}_{positive,negative}/`,
each carrying a minimal Django framework marker (`manage.py` with
`import django`, so `detect_frameworks` fires) plus exactly the config
shape under test. Positive fixtures plant the leaking configuration
(literal `DEBUG = True`, `devtool: 'source-map'`, `autoindex on;`, a
broad Dockerfile `COPY` with no `.dockerignore`, a `public-read` ACL
grant, a hardcoded secret literal in a tracked bundle); negative
fixtures use the identical shape with the leak closed (env-derived
`DEBUG`, `hidden-source-map`, `autoindex off;`, a `.dockerignore`
excluding `.git`, a `private` ACL, a runtime-injected config value), to
prove the rule does not fire on the clean case. WEBSEC311's second
detection path (a tracked `.js.map` file with no `devtool` config
involved) has its own
`webesc311_map_{positive,negative}` fixture pair and test.

frob:ticket T-5329
