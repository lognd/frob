## Done report

Root-caused live while re-measuring chunk3a
(tests/test_gates_suppress.py::TestSuppress001Gate::test_mypy_suppressed_ty_unsuppressed_fires
failing 'assert 3 == 1' on current main). T-3191 (already landed,
working exactly as designed, not the bug) changed
frob.check._python._run_ty to invoke `ty check` once per target
platform (linux/win32/darwin) and union all three platforms'
diagnostics into one list, each tagged `[platform=<name>]` so a
platform-only finding is attributable at a glance -- deliberate.

frob.gates._suppress._ty_diagnostics read result.diagnostics and
appended one (relfile, line, code) tuple per diagnostic with no dedup.
Before T-3191 this was safe (ty ran once, one diagnostic meant one
location). After T-3191, a genuinely cross-platform mismatch (the SAME
file:line:code on all 3 platforms, the common case) now legitimately
appears 3 times in the union. _suppress001_correlate iterates that list
directly with no dedup either, so it fired one SUPPRESS001 violation
per occurrence instead of once for a single real mismatch.

Fix: _ty_diagnostics now deduplicates by (relfile, line, code) before
returning. SUPPRESS001's actual question is "does ANY dialect report
this unsuppressed here" -- a presence check, not a per-platform count.
The platform tag T-3191 added stays intact on the underlying ty
ToolResult/Diagnostic objects for every OTHER consumer (the ty gate's
own report); only this one downstream consumer, which implicitly
assumed single-invocation cardinality, changes.

Confirmed no overlap with in-flight work: the OTHER 3 failures in the
same baseline chunk (test_check_coverage_registry.py x2,
test_gates.py::TestKnownGateRuleIds) share a DIFFERENT root cause
(REG002: VERSION001/TDD001/VMOD001 missing from _KNOWN_GATE_RULES) that
is already being fixed by another agent's in-progress
T-3376 (leases src/frob/gates/_waive.py) plus queued T-3239 --
left untouched, no collision.

## Done report

Changed:
src/frob/gates/_suppress.py::_ty_diagnostics

Evidence:
tests/test_gates_suppress.py::TestSuppress001Gate::test_mypy_suppressed_ty_unsuppressed_fires (1 passed, was the failing repro)
tests/test_gates_suppress.py::TestSuppress001Gate::test_ty_suppressed_mypy_unsuppressed_fires (1 passed, mirror-direction regression guard)
Also ran clean (not bound as evidence, broader sanity): tests/test_gates_suppress.py full file (17/17).

Filed: none new (this ticket is itself the filing for this root cause; the sibling REG002 root cause was already filed as T-3239/T-3376 by another agent before this session started)

Gates: frob check --ticket T-3374 --only archgate --only
affect_drift --only scope --only coverage --only fmt: gate:COV clean (0
errors), gate:AFFECT clean (frob.graph affects confirms
_ty_diagnostics is private with no doc/test binding, so no AFFECT001
applies), gate:ARCH's repo-wide 4-error count is unrelated pre-existing
ARCH103 findings in other files (app/_version_guard.py,
app/check_runner.py, app/ticket_runner/_land_cmd.py,
refactor/_verify.py), none touching src/frob/gates/_suppress.py.
ruff-format clean on the touched file. Full unscoped frob check was not
completed cleanly this session -- times out under current host load
(23+ concurrent worktrees, T-3247's known contention); ran targeted
--only families instead covering everything relevant to this diff.

### Changed
```
 src/frob/gates/_suppress.py        | 25 ++++++++---
 tickets/T-3375/ticket.md | 35 +++++++++++++++
 tickets/T-3374/ticket.md | 89 ++++++++++++++++++++++++++++++++++++++
 tickets/T-3377/ticket.md | 29 +++++++++++++
 4 files changed, 173 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/test_gates_suppress.py::TestSuppress001Gate::test_mypy_suppressed_ty_unsuppressed_fires` (pytest node id, verified passing when recorded)
- `tests/test_gates_suppress.py::TestSuppress001Gate::test_ty_suppressed_mypy_unsuppressed_fires` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 48 error(s), 3940 warning(s), 883 waived
- error-findings: ARCH103@src/frob/app/_version_guard.py, ARCH103@src/frob/app/check_runner.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/refactor/_verify.py, CLAUDE001@.claude/hooks/sync-claude-config.py, CYCLE001@src/frob/__init__.py, DEPR006@frob-deprecated-baseline.lock.json, DOC002@src/frob/tickets/_leases.py, DOC004@docs/commands/check.md, DOC005@docs/modules/cli.md, DOC007@src/frob/app/check_runner.py, DOC011@docs/guides/release.md, DOC011@docs/modules/tickets.md, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, DRIFT002@src/frob/app/check_runner.py, FLAGCOV001@frob.toml, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, LEXCHECK001@src/frob/gates/_comment_placement.py, OPAQUE001@tests/unit/test_land_finish_idempotent.py, PERF004@.claude/hooks/frob-suggest.py, PERF004@src/frob/lang/_support.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REG002@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, REL001@strata-core/src/graph/vmodel.rs, REL001@strata-core/src/parse/grammar_core.rs, REL001@tests/unit/test_conftest_suite_result_status.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/test_worktree_guard.py, SELFAUDIT001@design, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE011@frob-ratchet.lock.json, WIRE002@src/frob/gates/_tdd_order.py, WIRE002@tests/conftest.py
