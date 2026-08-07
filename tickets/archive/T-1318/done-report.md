## Done report

Root cause (per the ticket body): `frob.app.telemetry.redact_command`'s
`finally`-block call on every CLI invocation used `from frob.gates._secrets
import _redact, _scan_line` -- and importing ANY submodule of the `frob.gates`
package always executes that package's own `__init__.py` first (ordinary
Python import semantics), which eagerly imports its entire heavy stage
roster (pii, arch, dup, vet._capability, testing, ...) as a side effect.
Measured cost: ~257ms on every single `frob` command, regardless of
subcommand, fired entirely AFTER the command's real output.

Fix: extracted the secret-detection engine (the `_SecretPattern` dataclass,
`_pat` builder, the 33-entry `_PATTERNS` table, `_redact`, `_scan_line`, and
their fake-marker/entropy helper dependencies -- `_looks_fake`,
`_looks_low_entropy`, `_fake_marker_reason`, the placeholder/template-shape
regexes) out of `src/frob/gates/_secrets.py` into a NEW, `frob.gates`-
independent package: `src/frob/security/_redact.py`. `frob.gates._secrets`
now imports these FROM the new module (the dependency direction the
ticket's own body names) rather than defining them -- it keeps only the
GATE-specific layer (Violation construction, Severity classification, the
file/text-scanning orchestration, the `frob:secret-fake` staleness/bare-
marker sub-gates) that `redact_command` never needed.

One real type-boundary decision: `_SecretPattern.severity` is a plain `str`
("error"/"warn") in the new module, not `frob.gates._models.Severity` --
`frob.gates._models` is itself a submodule of `frob.gates`, so importing it
would reintroduce exactly the cost this ticket exists to remove.
`frob.gates._secrets._secret_violation` converts via `Severity(pattern.
severity)` (a StrEnum accepts its own value string) at its own
Violation-construction call site, the one place that actually needs the
enum type. All 33 `_pat()` call sites' severity arguments were mechanically
converted (Severity.ERROR -> "error", Severity.WARN -> "warn"), verified
against the original file's exact (provider, severity) pairs before/after
the transform (not uniform -- correctly preserved per-provider, e.g.
"stripe-secret-test"/"twilio-account-sid"/"plaid"/"basic-auth-url"/"jwt"
stayed WARN, everything else stayed ERROR).

Verification (the ticket's own explicit ask -- "verify with an import-cost
or import-graph assertion test"): tests/unit/security/test_redact.py, a
subprocess-based import-graph test (same precedent as T-1216's
tests/unit/test_app_lazy_exports.py):
  - importing frob.security._redact alone never loads frob.gates
  - calling frob.app.telemetry.redact_command never loads frob.gates
  - redact_command still correctly redacts a real-looking token
  - frob.gates._secrets still re-exports the same _redact/_scan_line
    objects (identity-checked, not just behaviorally)
  - every _PATTERNS entry's severity string round-trips through
    Severity(pattern.severity) cleanly

Measured directly (uv run python -c ...): `import frob.security._redact`
leaves 'frob.gates' NOT in sys.modules; calling redact_command with a real
Anthropic-shaped token confirms both the redaction still works AND
frob.gates stays unloaded.

Regression safety: the full pre-existing tests/test_secrets_gate.py suite
(79 tests covering every provider pattern, fake-marker discharge, entropy
heuristics, SEC001-SEC004) passes unchanged against the extracted module,
plus tests/test_telemetry.py and tests/unit/test_app_telemetry_branches_
t1400.py (telemetry's own suite) -- 133 tests total, all green.

Scope widened (frob ticket scope --add, each with a recorded reason): the
new src/frob/security/** package itself (the ticket's own proposed fix
location), tests/unit/security/** for the new import-graph test,
tests/test_secrets_gate.py (one frob:tests directive retargeted to the
moved _redact's new location), and docs/guides/extending/secrets-scan-
providers.md (one frob:describes anchor retargeted the same way).

DISCLOSED CUT: docs/modules/gates.md also carries one stale
`frob:describes src/frob/gates/_secrets.py::_redact` anchor that needs the
same one-line retarget -- could NOT fix it: that file is currently leased
by in-progress T-1205 (ScopeLeaseConflict on `frob ticket scope --add`).
Filed T-1538 to fix it once that lease frees; it is the ONLY
remaining DRIFT002 finding under `frob check --only secrets --only
coverage --only sys --only prework --only wire --ticket T-1318` (confirmed
by running each gate family individually, unscoped `--only secrets` included).

ALSO DISCLOSED, NOT caused by this ticket: `frob check --only coverage
--ticket T-1318` also reports 14 COV002 findings under src/frob/perf/
_hotpath_smells.py and src/frob/gates/_waive.py -- these are T-1225's own
committed symbols (verified: `git log --oneline` shows ce35f099 "T-1225 add
PERF010/011/013/014..." as the commit that introduced them, several commits
before T-1318 started). They pass cleanly under `--ticket T-1225`'s own
active-ticket scope resolution; they only surface under `--ticket T-1318`
because `_scope_covers`'s ambiguous-tie rule sees BOTH T-1225 (still
in-progress, scope src/frob/perf/**) and a T-1350-grace-window match
(T-1350's own now-landed-locally scope also names src/frob/perf/**) as
equally-specific candidates once T-1318's own active-ticket short-circuit
no longer applies -- an artifact of running three sequential tickets in one
unlanded worktree, not a T-1318 defect. Confirmed via `git diff main
--diff-filter=D --stat` showing zero unintended deletions from T-1318's own
work (one unrelated pre-existing file addition from a since-landed sibling
ticket, T-1528, not yet merged into this worktree).

Gates: frob check --only test --only archgate --only coverage --only sys
--only secrets --only prework --only wire --ticket T-1318, run per family,
all 0 errors except the one disclosed lease-blocked DRIFT002 above.

### Changed
```
 design/frob.strata                                 | 1681 +++++-----
 docs/design/registry/check-coverage.yaml           |   18 +-
 docs/guides/extending/secrets-scan-providers.md    |    2 +-
 docs/modules/gates.md                              |   11 +-
 docs/modules/perf.md                               |   11 +
 frob.lock                                          |   20 +
 src/frob/app/telemetry.py                          |   23 +-
 src/frob/gates/_pii_structural/_self_match.py      |    2 +
 src/frob/gates/_secrets.py                         |  603 +---
 src/frob/gates/_waive.py                           |    8 +
 src/frob/perf/__init__.py                          |   11 +
 src/frob/perf/_hotpath_smells.py                   |  302 ++
 src/frob/perf/_rules.py                            |   13 +-
 src/frob/security/__init__.py                      |   14 +
 src/frob/security/_redact.py                       |  663 ++++
 tests/test_secrets_gate.py                         |    2 +-
 tests/unit/perf/test_harness_main_branches.py      |  112 +
 tests/unit/perf/test_hotpath_smells.py             |  216 ++
 .../unit/perf/test_serial_pools_import_failure.py  |  102 +
 tests/unit/security/__init__.py                    |    0
 tests/unit/security/test_redact.py                 |  107 +
 tickets.md                                         | 3442 ++++++++++++++++----
 22 files changed, 5344 insertions(+), 2019 deletions(-)
```

### Evidence
- `tests/unit/security/test_redact.py::TestRedactModuleImportGraph::test_importing_redact_module_never_loads_frob_gates` (pytest node id, verified passing when recorded)
- `tests/unit/security/test_redact.py::TestRedactCommandImportGraph::test_calling_redact_command_never_loads_frob_gates` (pytest node id, verified passing when recorded)
- `tests/unit/security/test_redact.py::TestRedactCommandImportGraph::test_redact_command_still_redacts_a_real_looking_token` (pytest node id, verified passing when recorded)
- `tests/unit/security/test_redact.py::TestGatesSecretsStillWorksViaTheExtractedModule::test_secrets_gate_module_still_exposes_redact_and_scan_line` (pytest node id, verified passing when recorded)
- `tests/unit/security/test_redact.py::TestGatesSecretsStillWorksViaTheExtractedModule::test_severity_round_trips_through_the_plain_string_boundary` (pytest node id, verified passing when recorded)
- `tests/test_secrets_gate.py::TestRedact::test_never_returns_the_token` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
