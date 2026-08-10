## Done report

T-1892's EvidenceCmdSilent refusal is correct (a zero-exit command with
empty stdout+stderr digests the sha256 of the empty string and proves
nothing) and was left untouched. The two failing fixtures asserted the
old, unsound contract by passing the literal command 'true'. Swapped
both for a chatty zero-exit command ('echo verified') that exercises
the accepted path, and added a new test in the same class,
test_evidence_cmd_silent_is_refused, that asserts a silent command IS
refused, so the accepted and refused behaviors are locked together in
the fixture that owns them. No escape hatch or bypass flag added.

Evidence: the three pytest node ids bound above, all green
  (uv run pytest tests/unit/test_app_runners_batch7.py::TestTicketEvidence tests/unit/test_app_runners_batch7.py::TestTicketArchive -q
   -> 7 passed, 0 failed).

Filed: T-1905 (renumbers at land) -- reverse-dependency
search below found 9 MORE pre-existing failures in other test files
caused by the same T-1892 tightening; fixing them is outside T-1902's
declared scope (this ticket's Description named exactly the two
listed tests), so filed as a follow-up rather than fixed silently.

Reverse-dependency search performed (per coordinator instruction):
  grep -rn 'evidence_cmd\s*=\s*"true"\|ticket_evidence_cmd\s*=\s*"true"' tests/ src/ docs/
This surfaced every test-file call site that sets ticket_evidence_cmd
(or CLI --evidence-cmd) to the literal 'true', not just T-1902's own
two named tests. Ran the full pytest suite for each additional file
found:
  tests/test_ticket_runner_archive_force.py  -> 3 of these fail
  tests/test_tickets_cmd_evidence.py         -> re-verified clean (not
                                                 in the actual failure
                                                 list; its own 'true'
                                                 use is on a path this
                                                 fixture doesn't hit)
  tests/test_ticket_leases.py                -> 6 of these fail
                                                 (3 more 'true' sites
                                                 in this same file did
                                                 NOT fail; re-verify
                                                 alongside the fix)
All 9 real failures filed under T-1905 with exact node ids
and the measured command. Did not touch design/frob.strata or
src/frob/gates/_fix_engine_sync.py (T-1900's active lease).

Gates: frob check --ticket T-1902 clean for every gate this ticket's
own scope touches (gate:SCOPE 0 errors, gate:COV 0 errors, gate:DRIFT
0 errors, gate:DUP 0 errors after a reasoned DUP001 waiver on the new
test, gate:PRE 0 errors after re-sweep). Remaining repo-wide FAILs
(ruff-format 68 files, ty 6 diagnostics, gate:REG 1 error in
docs/design/registry/*.yaml) are pre-existing and unrelated to the
touched file -- ruff format --diff on this file shows only stale
formatting at lines the ticket never touched (module docstring
blank-line, unrelated monkeypatch calls elsewhere in the file); the
REG errors are dangling registry/rule-id mismatches in yaml this
ticket never opened.

### Changed
```
 tests/unit/test_app_runners_batch7.py | 36 ++++++++++++++++++--
 tickets/T-1902/ticket.md              | 16 ++++++++-
 tickets/T-1905/ticket.md    | 62 +++++++++++++++++++++++++++++++++++
 3 files changed, 111 insertions(+), 3 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 5 error(s), 807 warning(s), 695 waived
- error-findings: PRE001@tickets/T-1902, REG002@docs/design/registry/check-coverage.yaml, invalid-argument-type@src/frob/app/ticket_runner/_lifecycle.py, invalid-argument-type@tests/test_tickets_scope_mutation.py, invalid-argument-type@tests/unit/gates/test_sys_interface_canonical_order.py
