## Done report

Changed:
- frob.toml (`[gates.severity] DEPR003` "error" -> "warn")
- tests/gates_suite/test_depr003_severity_override.py (new file, 2 tests)

Evidence:
- tests/gates_suite/test_depr003_severity_override.py::test_depr003_survives_repo_severity_overrides
- tests/gates_suite/test_depr003_severity_override.py::test_depr003_not_forced_to_error_in_this_repo

Filed: T-draft-b368eee4 (SCOPE002 private-helper closure resolves calls by
bare short name, not import binding -- found while writing this ticket's
own regression test; filed from a throwaway worktree off main rather than
from T-3912's own branch, since filing it there would have polluted
T-3912's scope diff with an unrelated ticket file and tripped SCOPE001)

Gates: frob check --ticket T-3912 clean (0 errors in T-3912's own scope;
the repo-wide DRIFT001 on run_coalesced_verification remains and is
T-3912's sibling task, not touched here)

Root cause and decision (as requested):

_depr003_violations (src/frob/gates/_debt_deprecated.py) already computes
Severity.WARN for a frob:deprecated directive still inside its sunset
window, and only escalates to Severity.ERROR via the separate DEPR004
check once sunset passes -- the in-window/past-sunset distinction already
exists correctly in code. The bug was purely frob.toml's [gates.severity]
table, which _apply_severity_overrides (src/frob/gates/_waive.py) uses to
re-severity ANY rule's violations after the gate computes them,
unconditionally forcing DEPR003 to error regardless of window status.
T-3844 promoted every rule that measured zero violations to "error" without
distinguishing "the code is clean" from "this condition has never fired
yet" -- DEPR003 was the second kind: no live frob:deprecated directive
existed until T-3906 added the first one, so the override was never
exercised until it silently broke a correct, working gate the same day.

Fixed by reverting the config override (frob.toml DEPR003 = "warn") rather
than changing the gate: the gate's DEPR003/DEPR004 split already draws the
right line, so the smallest correct change is letting DEPR003 report the
severity it computes instead of a config table clobbering it after the
fact. Changing the gate code itself was unnecessary and would have
duplicated logic DEPR004 already owns.

On the broader question: yes, a rule whose CODE says Severity.WARN and
whose CONFIG's [gates.severity] table says "error" for that same rule
(with no severity-dependent branching by design) is a state that should be
mechanically detectable and probably its own gate/lint -- it is exactly
the SCOPE002-style "config statically contradicts code" shape, and DEPR003
would have failed the day of its very first live use even under a careful
review, because nothing measured "the config forces every WARN violation
of this rule to ERROR". A cheap version: for any rule where the gate ever
constructs a Violation with severity=Severity.WARN in its source (a static
grep over the gates package), flag a frob.toml [gates.severity] entry of
"error" for the same rule id as suspicious-by-default, requiring an
explicit frob:waive-style acknowledgment (with a reason) rather than a
bare toml assignment. This wouldn't have caught SCOPE002/T-3902 (a
different shape -- that one's gate code likely branches severity by
condition, similar to DEPR003/DEPR004's split) but would catch this exact
class: a rule with a SINGLE hardcoded WARN construction, promoted to
"error" wholesale by T-3844's zero-measurement sweep with no dynamic-else
severity path to justify it.

### Changed
```
 frob.toml                                          |  2 +-
 .../gates_suite/test_depr003_severity_override.py  | 60 +++++++++++++++++++++
 tickets/T-3912/ticket.md                           | 61 +++++++++++++++++++++-
 3 files changed, 121 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/gates_suite/test_depr003_severity_override.py::test_depr003_survives_repo_severity_overrides` (pytest node id, verified passing when recorded)
- `tests/gates_suite/test_depr003_severity_override.py::test_depr003_not_forced_to_error_in_this_repo` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 1 error(s), 4382 warning(s), 930 waived
- error-findings: DRIFT001@src/frob/verify/_worker.py
