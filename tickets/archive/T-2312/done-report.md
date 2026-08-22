## Done report

T-2312's mechanism is fixed. `_file_regression_ticket`'s `new_ticket(...)`
failure branch (now split into `_dispose_to_existing_duplicate_or_none`,
ARCH001) resolves a `DuplicateTicket` refusal to the existing ticket via
`_find_exact_duplicate` and disposes the covered findings to it -- the
same effect as if this call had just filed a fresh regression ticket --
instead of logging an error and leaving the findings ownerless with
quarantine pinned. Every other filing failure (acceptance [1]'s
must-still-pass positive control) still returns None and leaves
quarantine raised, unchanged.

`clear_quarantine`'s undisposed-refusal branch (now split into
`_refuse_if_undisposed`, ARCH001) also diagnoses a path-shape mismatch
(`_path_shape_hint`): when the quarantine store holds an absolute-path
identity and an operator's `--file-ticket` key uses a relative one (or
vice versa), the refusal now names the mismatch instead of leaving a
bare FindingsNotDisposed.

Acceptance [2] (fleet status / land refusal must state raised quarantine
+ undisposed count without needing `frob verify status`) was already
satisfied by pre-existing code -- `scripts/fleet_status.py`'s
`QUARANTINE RAISED -- N undisposed...` line and
`_land_cmd.py::_quarantine_override_ceilings`'s land-refusal message --
verified directly, not re-implemented.

Repro: `test_duplicate_title_disposes_to_existing_ticket_instead_of_dropping`
fails at the pre-fix commit (f21e54625) and passes after the fix.
Positive controls: `test_non_duplicate_filing_failure_still_leaves_quarantine_raised`
(a non-duplicate filing failure must still leave quarantine raised) and
`test_path_shape_mismatch_is_diagnosed_not_a_bare_refusal` (the mismatch
must still refuse, only the diagnosis is new). All pass:
`tests/unit/test_rapid_sweep.py::TestFileRegressionTicket` 7/7,
`tests/unit/verify/test_quarantine.py` 23/23.

Both functions grew past ARCH001's long-and-complex threshold after the
initial fix (caught by the coordinator's land attempt); split into
`_dispose_to_existing_duplicate_or_none` and `_refuse_if_undisposed`,
each with its own docstring, rather than waived. `ty` clean after adding
TYPE_CHECKING-only imports for the split helper's annotations and
narrowing `_refuse_if_undisposed`'s return type to a plain
`QuarantineError | None`.

### Changed
```
 src/frob/app/ticket_runner/_rapid_sweep.py |  71 ++++++++++++++++---
 src/frob/verify/_quarantine.py             | 106 +++++++++++++++++++++++++----
 tests/unit/test_rapid_sweep.py             |  89 ++++++++++++++++++++++++
 tests/unit/verify/test_quarantine.py       |  39 +++++++++++
 tickets/T-2312/ticket.md                   |  52 ++++++++++++--
 5 files changed, 331 insertions(+), 26 deletions(-)
```

### Evidence
- `tests/unit/test_rapid_sweep.py::TestFileRegressionTicket::test_duplicate_title_disposes_to_existing_ticket_instead_of_dropping` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestFileRegressionTicket::test_non_duplicate_filing_failure_still_leaves_quarantine_raised` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_quarantine.py::TestClearQuarantine::test_path_shape_mismatch_is_diagnosed_not_a_bare_refusal` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, AFFECT001@src/frob/app/ticket_runner/_rapid_sweep.py, AFFECT001@src/frob/verify/_quarantine.py, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@scripts/fleet_status.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/release/_cli.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/tickets/_land_git_ops.py, COV001@src/frob/verify/_drain.py, COV001@src/frob/verify/_quarantine.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV005@src/frob/app/ticket_runner/_rapid_sweep.py, COV005@src/frob/verify/_quarantine.py, DOC001@docs/commands/release.md, DOC002@src/frob/app/verify_runner.py, DOC002@src/frob/verify/_drain.py, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/gates/_fmt_directives.py, DRIFT002@scripts/fleet_status.py, DRIFT002@src/frob/verify/_drain.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PERF004@src/frob/app/ticket_runner/_new.py, PRE001@tickets/T-2312, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK004@tickets.md, WIRE003@docs/modules/cli.md
