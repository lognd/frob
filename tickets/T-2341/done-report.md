## Done report

Re-measured the current floor against T-2331's carried-forward 19-identity
claim list rather than trusting it, per the caveat: T-2322 has since split
_land_cmd.py's ARCH functions, exactly the file this ticket's original
scope leaned on most.

RESOLVED (not reproduced on the current floor, verified via frob check
--only archgate/docanchor/perf against unmodified main; scope narrowed
accordingly): all 5 ARCH001 (telemetry.py:189, _land_cmd.py:1969/2995/3443,
_new.py:474), 2 of 3 ARCH103 (_land_cmd.py:3515/3599), DOC001
(docs/commands/release.md), both PERF004 (_land_cmd.py:3494, _new.py:984).

FIXED IN THIS TICKET:
- ARCH103 fleet_status.py:1549 (_print_rot_bucket mixing I/O + formatting
  + 4 decision points): split into _rot_bucket_lines (pure formatting/
  branching, no I/O, independently testable) and a thin _print_rot_bucket
  I/O wrapper. Verified: tests/system/test_fleet_status_ticket_readiness_
  arch001.py and tests/unit/test_coordinator_scripts.py -k Rot (11 tests)
  both still pass; frob check --only archgate no longer reports it.
- COV001 x5: added frob:doc edges for scripts/fleet_status.py::
  VERIFY_QUEUE/VERIFY_WATERMARK/verify_queue_state (new #verify_queue_
  state anchor + section added to docs/guides/coordinator-scripts.md,
  documenting the real (depth, oldest_age_s)/(-1, None) return contract
  read from the function's own docstring, not guessed),
  src/frob/tickets/_land_git_ops.py::detect_duplicate_ticket_id_
  collisions (new section in docs/modules/tickets-landing.md, scope
  widened to include that file), src/frob/verify/_quarantine.py::
  clear_quarantine (same shared #quarantine-circuit-breaker-t-1693 anchor
  every other public symbol in that module already uses).
- DOC002 x3: the two fleet_status.py occurrences of the broken
  #verify_queue_state anchor now resolve (the section above fixes both);
  src/frob/app/verify_runner.py's #automatic-watermark-drain-t-2310
  anchor corrected to the real slug
  #automatic-watermark-drain-rapid-only-t-2310.

Verified with frob check --only coverage --only docanchor --only archgate:
0 COV001/DOC002/ARCH103 findings remain for any of the fixed identities
(re-run three times across the fix iterations, each time confirming the
specific (rule, file) identity is gone from output, not just an aggregate
count drop). ruff check/format clean on every touched file. Existing test
coverage (tests/unit/test_coordinator_scripts.py -k "Rot or VerifyQueue or
Leases", tests/unit/verify/test_quarantine.py, tests/unit/
test_land_duplicate_ticket_id.py, tests/system/test_fleet_status_ticket_
readiness_arch001.py) all pass unmodified against the refactor/doc fixes.

SPLIT OUT (their own dispatches, children filed): COV003 x4 (T-1205/
T-1235/T-1397/T-1526's bound evidence does not resolve against tests/
unit/test_makefile_coverage.py) -> T-2366. TICK004 (tickets.md
ledger-consistency, 9 errors + 17 warnings under one identity, needs
per-finding triage before a fix) -> T-2367.

STILL OPEN in this ticket's own (narrowed) scope, not attempted this
pass: SELFAUDIT001 (design, live but now 9 findings not 21 -- ratchet-
based, drifts run to run, needs its own investigation per the ticket's
original plan) and WIRE003 (docs/modules/cli.md's 'path' verb reference,
confirmed still live, not yet diagnosed).

Scope was narrowed via frob ticket scope --remove for every file whose
only claimed finding is now resolved (telemetry.py, _land_cmd.py, _new.py,
docs/commands/release.md, and the four COV003 ticket dirs now split to
T-2366), and --add for docs/modules/tickets-landing.md (needed for the
detect_duplicate_ticket_id_collisions doc section).

### Changed
```
 tickets/T-2341/ticket.md | 316 +++++++++++++++++++++++++++++++++++++++++++++--
 1 file changed, 307 insertions(+), 9 deletions(-)
```

### Evidence
- `tests/unit/test_coordinator_scripts.py::TestVerifyQueueState::test_reports_depth_and_oldest_age` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_quarantine.py::TestClearQuarantine::test_refuses_when_not_raised` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_duplicate_ticket_id.py::TestDetectDuplicateTicketIdCollisions::test_flags_id_with_genuinely_different_content_on_both_sides` (pytest node id, verified passing when recorded)
- `tests/system/test_fleet_status_ticket_readiness_arch001.py::TestFleetStatusTicketReadinessArch001::test_ticket_readiness_is_not_an_arch001_finding` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: AFFECT001@src/frob/verify/_quarantine.py, ARCH103@src/frob/release/_cli.py, COV001@src/frob/verify/_drain.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, DOC001@docs/commands/release.md, DOC002@src/frob/verify/_drain.py, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2341/src/frob/verify/_worker.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_new.py, PRE001@tickets/T-2341, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md
