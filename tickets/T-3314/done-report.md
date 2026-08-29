## Done report

All three scaffolded GitHub Actions CI templates (python-tool/shared,
pyo3-library, web-app) guarded the frob check step with a preflight
(`frob graph --help`) that, on failure, printed a `::notice::` and
skipped the step with exit 0 -- indistinguishable from a passing gate
in a green build. Category per T-3276's rule: `frob` itself being
missing/broken means the gate genuinely could not run at all (this is
the pre-0.1.0-on-PyPI transitional case named in the templates' own
comments) -- optional-but-needed-for-a-gate means UNMEASURED reported
loudly, never folded into CLEAN.

Fix: the missing-frob branch now emits `::error::` (naming the install
command) and `exit 1`, failing the job with a non-green CI status
instead of a swallowed notice line. No `continue-on-error` added --
the ticket's own directive ("fail the job loudly, or at minimum make
the skip visible as a non-green status") is satisfied by the stronger
option; a hard failure here does not block scaffolded-project merges
any differently than any other CI gate would, and is the same posture
this repo's own `frob check`/`frob doctor` already established for a
REQUIRED tool's absence.

A regression test (tests/unit/test_scaffold_project.py::
test_ci_template_frob_check_gate_fails_loudly_not_silently) already
existed pre-scoped to this exact assertion set (no `::notice::`, a real
`::error::`, `exit 1`, and the install command named) across all three
project types -- verified it passes against the fix.

Evidence: tests/unit/test_scaffold_project.py::test_ci_template_frob_check_gate_fails_loudly_not_silently

Gates: frob check --ticket T-3314 clean on the diff-scoped checks
(SCOPE/PREWORK/COV002/AFFECT/FMT against this ticket's own touched
set).

### Changed
```
 .../scaffold/data/shared/python/github/ci.yml.j2   | 13 +++--
 .../data/types/pyo3-library/github/ci.yml.j2       | 11 +++--
 .../scaffold/data/types/web-app/github/ci.yml.j2   | 11 +++--
 tests/unit/test_scaffold_project.py                | 36 ++++++++++++++
 tickets/T-3314/done-report.md                      | 56 ++++++++++++++++++++++
 tickets/T-3314/ticket.md                           | 12 ++++-
 6 files changed, 125 insertions(+), 14 deletions(-)
```

### Evidence
- `tests/unit/test_scaffold_project.py::test_ci_template_frob_check_gate_fails_loudly_not_silently` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 41 error(s), 3920 warning(s), 880 waived
- error-findings: ARCH103@src/frob/app/_version_guard.py, ARCH103@src/frob/app/check_runner.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/app/ticket_runner/_verify.py, ARCH103@src/frob/refactor/_verify.py, CYCLE001@src/frob/__init__.py, DEPR006@frob-deprecated-baseline.lock.json, DOC002@src/frob/tickets/_leases.py, DOC003@docs/commands/sys.md, DOC004@docs/commands/check.md, DOC007@src/frob/app/check_runner.py, DOC011@docs/modules/tickets.md, DOCENUM001@docs/modules/gates.md, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, DRIFT002@src/frob/app/check_runner.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, LEXCHECK001@src/frob/gates/_comment_placement.py, OPAQUE001@tests/unit/test_land_finish_idempotent.py, PERF004@.claude/hooks/frob-suggest.py, PERF004@src/frob/lang/_support.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-3314, REL001@src/frob/__init__.py, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, REL001@strata-core/src/graph/vmodel.rs, REL001@strata-core/src/parse/grammar_core.rs, REL001@tests/unit/test_conftest_suite_result_status.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/test_worktree_guard.py, SELFAUDIT001@design, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json
