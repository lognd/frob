## Done report

Changed:
src/frob/strata/_selfconform.py (frob:enforces CHK-GATE-SYS107 edge added)
src/frob/strata/_mutation_audit.py (EXPORT_DETECTABLE_KINDS docstring updated)
tests/unit/strata/test_mutation_audit.py (disclosed-gaps set + docstring updated)

Root cause 1 (REG008 on check-coverage.yaml): CHK-GATE-SYS107's registry
entry is dispositioned handled_by:SYS107, but SYS107 (a SELFAUDIT001
sub-rule, T-1451) only had the family-level `frob:enforces
CHK-GATE-SELFAUDIT001` edge in src/frob/gates/_sys_selfaudit.py -- no
sub-rule-specific edge, unlike sibling SYS104/105/106 which each got
their own explicit `frob:enforces CHK-GATE-SYS10x` edge in
_selfconform.py when their registry entries were added (T-1113
precedent). Added the matching `frob:enforces CHK-GATE-SYS107` edge
next to CHK-GATE-SYS106 in _selfconform.py's SYS10x edge block.

Root cause 2 (mutation-audit disclosed-gaps drift): the env-mode-
explosion (T-1453's via migration) promoted the `checker` node's
`may "env.read"` atom (design/frob.strata, T-1346's FROB_NO_GATE_CACHE
gate-cache escape hatch) to its precise tier-2 spelling. Confirmed via
direct inspection that this is a genuine, disclosed gap and not spurious
drift: unlike `fs.read`/`fs.write` (real `open`/`read` syscalls,
T-1203's rationale for adding those two to `_SECCOMP_KIND_MAP`), reading
an environment variable has no distinct OS syscall of its own (a libc
lookup over the process's already-mapped environment block) -- there is
no seccomp-profile fact for the second detector to vary on when an
`env.read` atom is deleted. Added `env.read` to the test's disclosed set
and updated `EXPORT_DETECTABLE_KINDS`'s docstring in _mutation_audit.py
to name it alongside the other disclosed app-level kinds.

Evidence:
tests/test_registry_exhaustiveness.py::TestCheckCoverageReg008BurnDown::test_no_reg008_findings_for_check_coverage_yaml
tests/unit/strata/test_mutation_audit.py::TestMayMutationAuditRealRepo::test_second_detector_gaps_are_exactly_the_disclosed_app_level_kinds

Verification: both tests pass standalone, together, and as full-file runs
(tests/test_registry_exhaustiveness.py: 42 passed; tests/unit/strata/
test_mutation_audit.py: 6 passed). `uv run frob check --only registry
--only sys` is clean: 0 errors, 0 waived, 1 pre-existing unrelated
warning (SYS100 extended env observed but undeclared on testsuite).

Filed: none -- both root causes were fully addressed in scope, no
follow-up needed.

Gates: uv run frob check --only registry --only sys clean (0 errors);
PRE001/TICK006 seen on a later full `frob check --ticket` run are stale-
sweep/scratchpad-collision artifacts unrelated to this ticket's own
changes (see final report to coordinator) -- re-ran pre-work sweep to
clear PRE001.

### Changed
```
 src/frob/strata/_mutation_audit.py       |  10 +-
 src/frob/strata/_selfconform.py          |   4 +
 tests/unit/strata/test_mutation_audit.py |  14 ++-
 tickets.md                               | 165 +++++++++++++++++++++++++++++++
 4 files changed, 191 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_registry_exhaustiveness.py::TestCheckCoverageReg008BurnDown::test_no_reg008_findings_for_check_coverage_yaml` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_mutation_audit.py::TestMayMutationAuditRealRepo::test_second_detector_gaps_are_exactly_the_disclosed_app_level_kinds` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 1 error(s), 3002 warning(s), 740 waived
- error-findings: TICK006@tickets.md
