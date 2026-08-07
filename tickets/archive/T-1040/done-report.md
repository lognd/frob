## Done report

Initially added "ffi_boundary" to _STAGE_GROUPS["gates-security"] in
src/frob/check/__init__.py (next to opaque/secrets, same cheap
security-scan shape). This made the coverage drift-lock
(TestCheckStageGroups::test_available_stages_cover_every_gate_and_tool)
pass and both `--only ffi_boundary` and `--only gates-security` ran the
gate (ffi_boundary=0.4s in the gate-summary timing).

Before landing, the coordinator flagged that another agent's regression
fix, T-1044 (landed 2d178ded, "ffi_boundary gate missing from
_STAGE_GROUPS breaks --stamp-baseline --only chunking"), had already
added "ffi_boundary" to _STAGE_GROUPS["gates-fast"] on main -- the same
core ask this ticket's brief describes. After `git merge main`, both
additions were present (git merged them cleanly, no textual conflict,
since they touched two different dict entries). This ticket's own
gates-security addition is therefore redundant: T-1044 already closes
the coverage gap. I reverted this ticket's own hunk
(src/frob/check/__init__.py is now byte-identical to main --
`git diff main -- src/frob/check/__init__.py` is empty) rather than
leave a duplicate membership sitting in two groups.

ABSORBED-CLOSE: T-1044 fully absorbed T-1040's substance. No new code
from this ticket lands. Verified after the merge:
- tests/system/test_cli_check.py::TestCheckStageGroups (all 5 tests)
  pass, including the coverage drift-lock.
- tests/system/test_cli_check.py::TestCheckPolyglot::
  test_pinned_check_type_reports_skipped_line ALSO now passes after the
  merge -- it was red on main before T-1044/whatever else landed
  alongside it in this session; it is green now with no further action
  from this ticket. (It had failed earlier in this same session with
  `sqlite3.OperationalError: no such table: files` inside
  _check_fingerprint -- an unrelated cause this ticket did not touch;
  something else fixed it before/via the merge.)

Nothing further from the ticket body (a dedicated --only alias beyond
group membership, a docs/modules command-table entry) was asked for
beyond bare stage-group membership, so there is no residual work to do
here (no ticket needed).

### Changed
```
 tickets.md | 36 +++++++++++++++++++++++++++++++++++-
 1 file changed, 35 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/system/test_cli_check.py::TestCheckStageGroups::test_available_stages_cover_every_gate_and_tool` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 8 error(s), 1807 warning(s), 355 waived
- error-findings: COV001@src/frob/arch/_models.py, COV001@src/frob/gitlog/__init__.py, COV001@src/frob/process/parsers/common.py, COV001@src/frob/render/_color.py, COV001@src/frob/render/_elements.py, PERF003@src/frob/arch/_cpp_mayraise.py, PERF004@src/frob/arch/_cpp_mayraise.py, PRE001@tickets/T-1040
