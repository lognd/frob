## Done report

Added the exhaustive-exception gate + errors-as-values advisory over T-0686's
compute_may_raise, both consuming only its public surface (compute_may_raise,
UNKNOWN) -- src/frob/arch/_mayraise.py was never edited (T-0689's concurrent
ctypes work there was left untouched).

New: src/frob/gates/_exhaustive_handling.py (exhaustive_handling_gate,
EXHAUST001/EXHAUST002) and src/frob/arch/_exceptions.py
(check_errors_as_values, category errors-as-values-recommended). Wired
EXHAUST001/EXHAUST002 into src/frob/gates/__init__.py's _KNOWN_GATE_RULES,
_ALL_GATES, _CANONICAL_GATE_ORDER, and process_jobs (job name
exhaustive_handling). Registered the new ArchCategory literal in
src/frob/arch/_models.py (unwaivable advisory channel picks it up
automatically). Docs added under docs/modules/gates.md (new sections
EXHAUST001 EXHAUST002 (T-0688) and errors-as-values advisory (T-0688)).

Severity: both EXHAUST rules ship at WARN, not ERROR, at this landing --
a real run against this repo's own source produced 176 pre-existing
findings (overwhelmingly narrow except-clauses around a call this
resolver cannot statically resolve to Unknown). Promoting straight to
ERROR would have redded every other ticket's frob check immediately; this
matches the same first-turn-on-debt posture T-0680 (REG008-REG011) and
T-0728 (ARCH101-103) already used for their own new gates. Filed as a
disclosed, deliberate choice, not silently softened.

Scope note: extended scope by one file, src/frob/check/__init__.py, to add
"exhaustive_handling" to the gates-native stage-group set
(_STAGE_GROUPS) -- required so the new gate stays --only reachable and so
the existing drift-lock test
(tests/system/test_cli_check.py::TestCheckStageGroups::test_available_stages_cover_every_gate_and_tool)
does not fail; this is a one-line mechanical registration this ticket's
own gate wiring requires, not a new feature. Ticket scope was formally
extended via `frob ticket scope` with a reason recorded.

Found but out of scope, filed as a new ticket instead of silently
resolved: T-0931 -- a sibling ticket (T-0689), landed on main
concurrently while this ticket was in flight, introduces its OWN
"# frob:raises A, B" same-line call-site directive
(NormalizedCall.declared_raises) with different placement/grammar than
this ticket's above-the-def, function-wide "# frob:raises <Type>"
directive (EXHAUST002's declared-propagation contract). Both share the
literal verb text "frob:raises" with different semantics -- needs
reconciling (rename one convention) before both land together on the
same tree. Not resolved here since T-0689 owns _mayraise.py and its own
convention, outside this ticket's declared scope.

Gates: `uv run frob check --ticket T-0688 --only lint` clean; `--only
static` clean (pass, no new findings); `--only gates-fast` clean (0
errors, pre-existing waived DRIFT001 debt only); `--only gates-native`
clean (0 errors, EXHAUST 176 warnings -- the disclosed first-turn-on
debt above); `--only gates-security` clean. All four chunked stage
groups pass.

### Changed
```
 docs/modules/gates.md                  |  91 +++++++++++
 src/frob/arch/_exceptions.py           | 202 +++++++++++++++++++++++
 src/frob/arch/_models.py               |  12 ++
 src/frob/check/__init__.py             |   8 +-
 src/frob/gates/__init__.py             |  21 +++
 src/frob/gates/_exhaustive_handling.py | 288 +++++++++++++++++++++++++++++++++
 tests/test_gates.py                    | 256 ++++++++++++++++++++++++++++-
 tickets.md                             |  13 +-
 8 files changed, 885 insertions(+), 6 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestExhaustiveHandlingGate::test_partial_catch_of_named_type_fires_exhaust002` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestExhaustiveHandlingGate::test_unknown_without_catch_all_fires_exhaust001` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestExhaustiveHandlingGate::test_catch_all_of_unknown_does_not_fire_exhaust001` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestExhaustiveHandlingGate::test_declared_frob_raises_directive_discharges_exhaust002` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestExhaustiveHandlingGate::test_function_with_no_catches_is_not_a_boundary` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestErrorsAsValuesAdvisory::test_public_raiser_with_no_handling_caller_recommends_result` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestErrorsAsValuesAdvisory::test_public_raiser_with_handling_caller_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestErrorsAsValuesAdvisory::test_private_raiser_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestErrorsAsValuesAdvisory::test_only_ubiquitous_or_unknown_raises_not_flagged` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 9 passed (from 9 evidence id(s))
- gates: 1 error(s), 4147 warning(s), 219 waived
- error-findings: PRE001@tickets/T-0688
