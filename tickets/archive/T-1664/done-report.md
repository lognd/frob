## Done report

Adds Severity.UNRESOLVED (src/frob/gates/_models.py): a THIRD, distinct
gate outcome, not a tier between warn and error. ERROR/WARN both mean
"the check ran to completion and this is what it found" (possibly an
empty violation list -- a real, complete answer). UNRESOLVED means "the
check could not determine an answer at all" -- the exact shape behind
every under-reporting incident this drive found (stale-natives PERF004
reading zero, an xdist mypy-cache oracle returning zero diagnostics for
a file that had one, a capability scanner's "no capabilities" meaning
either "checked, clean" or "cannot analyse this language").

Wired the counting/rendering half only, per the ticket's own explicit
scope discipline:
- _unresolved_count (src/frob/check/_python.py) counts UNRESOLVED
  violations.
- _gates_family_result / _gates_summary now report error/warning/
  unresolved/waived as four always-shown terms (T-0228's "never
  collapse" precedent extended one term further) -- an UNRESOLVED
  finding can never be folded into "N warnings", indistinguishable
  from a real completed finding.
- Exit code stays gated on n_err alone in both places -- UNRESOLVED
  never fails a run by itself. Converting every hard-to-resolve case
  into an auto-fail would flood a floor that is currently zero and make
  the signal worthless (explicit anti-goal from the brief).
- _diag_severity maps UNRESOLVED to a Diagnostic "info" severity
  (distinct from "error"/"warning") when rendered through the shared
  process/parsers Diagnostic model.

Deliberately NOT built this pass (disclosed in docs/modules/gates.md,
not silently dropped): a generic per-gate "declares its optional
substrate and auto-reports UNRESOLVED when absent" mechanism (item 2 of
the ticket) -- that is real per-gate wiring work each family needs
individually. REF001 (T-1665) was investigated as the intended first
concrete consumer; reported separately (see T-1665's own Done report /
follow-up ticket) as needing a real resolved-import substrate that does
not exist yet in frob.graph, rather than force a half-measure into a
carefully-tuned, already three-times-hardened 795-line module under
time pressure.

### Changed
```
 docs/modules/gates.md                  |  56 +++++++++++++-
 src/frob/check/_python.py              |  73 ++++++++++++++----
 src/frob/gates/_models.py              |  26 ++++++-
 tests/unit/test_check_gates_summary.py | 137 +++++++++++++++++++++++++++++++++
 tickets/T-1664/ticket.md               |  73 +++++++++++++++++-
 5 files changed, 345 insertions(+), 20 deletions(-)
```

### Evidence
- `tests/unit/test_check_gates_summary.py::TestSeverityUnresolved::test_unresolved_is_a_distinct_severity_value` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_gates_summary.py::TestUnresolvedCount::test_counts_only_unresolved_violations` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_gates_summary.py::TestUnresolvedCount::test_zero_when_no_unresolved_present` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_gates_summary.py::TestDiagSeverity::test_error_maps_to_error` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_gates_summary.py::TestDiagSeverity::test_warn_maps_to_warning` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_gates_summary.py::TestDiagSeverity::test_unresolved_maps_to_info_not_warning` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_gates_summary.py::TestGatesFamilyResultUnresolved::test_unresolved_findings_never_fail_the_family` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_gates_summary.py::TestGatesFamilyResultUnresolved::test_unresolved_count_shown_as_its_own_term_not_folded_into_warn` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_gates_summary.py::TestGatesFamilyResultUnresolved::test_errors_still_fail_the_family_regardless_of_unresolved` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_gates_summary.py::TestGatesSummaryUnresolved::test_summary_line_names_unresolved_as_its_own_term` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_gates_summary.py::TestGatesSummaryUnresolved::test_zero_unresolved_still_names_the_term` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 11 passed (from 11 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: F401@/home/logan/projects/frob/.claude/worktrees/rule-bookkeeping/tests/unit/test_tickets_evidence_only_scope.py, PRE001@tickets/T-1664
