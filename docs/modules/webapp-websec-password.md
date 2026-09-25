# frob.webapp._websec_password -- WEBSEC218-224 password policy and storage

One sentence: `frob.webapp._websec_password.websec_password_findings`
extends the same taint call site (`frob.gates._taint_gate.taint_gate`)
with a password-policy/storage family -- missing controls (no
breach-password check, no email-verification gate) and weak
cryptographic primitives/config around password storage (MD5/SHA1
hashing, AES-ECB, a hardcoded IV, a default seed-data account, a
case-folded comparison) -- folded into `taint_gate`'s own scan rather
than a second gate registration (the same reasoning T-5307's
`docs/modules/webapp-websec-injection.md`, T-5308's
`docs/modules/webapp-websec-headers-log.md`, T-5329's
`docs/modules/webapp-websec-debug-config.md`, and T-5352's
`docs/modules/webapp-websec-jwt-oauth.md` already document).

This is a downstream leaf of the T-5140 web-app epic's substrate wave
(docs/modules/webapp.md's own scope: framework detection only, not any
individual rule family).

## Framework gating

`websec_password_findings(root)` calls
`frob.webapp._detect.detect_frameworks` first and returns `()`
immediately for a repo with no detected web framework -- the same
short-circuit every WEBSEC/COMPLY/A11Y/SEO/WEBPERF family uses (T-5302).
This module never re-implements framework sniffing.

## Rule catalog

| rule | check | evidence | detection |
| --- | --- | --- | --- |
| WEBSEC218 | a privileged-action call in a file with no `email_verified`/`is_verified` check anywhere in that file | Python/JS backend, file-scope | text-regex |
| WEBSEC219 | a `set_password`/`hash_password` call in a file with no breach-password check anywhere in that file | Python/JS backend, file-scope | text-regex |
| WEBSEC220 | `hashlib.md5(`/`hashlib.sha1(` on a line that also mentions `password`/`pwd`/`passwd` | Python backend | text-regex |
| WEBSEC221 | `MODE_ECB`/an `"aes-*-ecb"`-shaped cipher-mode string | Python/JS backend | text-regex |
| WEBSEC222 | an `iv`/`nonce`-named variable assigned a hardcoded hex/byte-string literal | Python/JS backend | text-regex |
| WEBSEC223 | a `seed`/`migration`/`fixtures`-path file assigning a default-looking credential to a `password`-named field | seed/migration data | text-regex |
| WEBSEC224 | a password comparison with `.lower()`/`.upper()` applied to either side | Python/JS backend | text-regex |

`WEBSEC225` is reserved but unimplemented in this leaf -- the ticket
body's seven-item corpus consumed only seven of the reserved eight ids;
the eighth is follow-up scope, see the T-5353 Done report for the
ticket id.

WEBSEC218 and WEBSEC219 are FILE-SCOPE checks, not per-function/
per-branch: a match anywhere in the same tracked file as the flagged
call site clears the finding, even if that check does not actually
guard the flagged call path. A real per-branch check would need
control-flow analysis this module does not attempt -- the same
disclosed granularity gap `_websec_headers_log`'s intra-line sanitizer
check already carries for a different axis (T-5308). The ticket body's
own "AST lint per sink" is approximated as a call/literal-site text
regex here, the same idiom `_websec_headers_log`/`_websec_debug_config`/
`_websec_tokens` already use for JS/TS evidence (`frob.lang`'s
identifier walker has no javascript/typescript entry yet, T-3232).

## Severity

WARN-tier at first turn-on -- the same T-0688/T-0973 promotion posture
`taint_gate`/`opaque_gate`/every sibling WEBSEC family already follows
for a brand-new structural rule.

## Public API

- `WebsecPasswordFinding` (`src/frob/webapp/_websec_password.py`) --
  one finding: `rule`, `file`, `line`, `message`.
- `websec_password_findings(root: Path) ->
  tuple[WebsecPasswordFinding, ...]` -- every WEBSEC218-224 finding
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
  `websec_password_findings` itself. `websec_findings` is a thin
  wrapper -- WARN-tier `Violation` construction only, no independent
  detection logic.

## Tests and fixtures

`tests/unit/test_websec_password.py` -- one positive-control and one
negative-control fixture per rule under
`tests/fixtures/webapp/websec2xx/password/webesc2{18..24}_{positive,negative}/`,
each carrying a minimal Django framework marker (`manage.py` with
`import django`, so `detect_frameworks` fires) plus exactly the
call/config shape under test. Positive fixtures plant the gap (a
privileged action with no verification check, `set_password` with no
breach check, `hashlib.md5(password...)`, `AES.MODE_ECB`, a hardcoded
`iv`, a `seed/`-path default credential, a `.lower()`-folded
comparison); negative fixtures use the identical shape with the gap
closed, to prove the rule does not fire on the clean case. This subdir
(`password/`) is this ticket's own fixture scope, distinct from the
sibling `csrf_session/` (T-5351) and `jwt_oauth/` (T-5352) subdirs
under the same `websec2xx/` parent.

frob:ticket T-5353
