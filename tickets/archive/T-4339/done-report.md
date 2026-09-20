## Done report

Root cause established (not assumed): `frob ticket new`'s CLI verb (`_new`
in `src/frob/app/ticket_runner/_new.py`) logged the `created <id>: <title>`
success line immediately after `new_ticket()` returned `Ok` -- BEFORE
`_commit_new_ticket_ledger_change_or_exit` ran. That commit step
(`commit_ticket_ledger_change`, `src/frob/tickets/_leases.py`, left
untouched -- held by another in-flight agent) can, on a `LandInProgress`
timeout, invoke `_rollback_pathspecs`, which runs `git clean -fd` over the
just-written, still-untracked ticket path -- discarding the ticket the CLI
had already told the caller existed. T-4313's own incident matches this
exactly: several lands and other ticket creations were running
concurrently at the filing timestamp; the rollback fired after the
success line printed; the surviving `.frob/tickets/T-4313.lock` (the
per-ticket `ticket_lock` file, under gitignored `.frob/` and therefore
never a candidate for the pathspec-scoped `git clean`) is the forensic
fingerprint of exactly this seam. Of the four candidate seams named in
the ticket body, this is the one that fired -- confirmed by tracing the
actual call order in `_new.py`, not by hardening all four on suspicion.

Fix: `_new` now runs the ledger commit and a mandatory read-back
(`_confirm_new_ticket_readback_or_exit`, new function, calls
`frob.tickets.load_all` and exits 1 with the id named if the ticket is
absent) BEFORE logging or JSON-emitting any success output. The success
line now can only ever follow a verified, durable write -- a rollback (or
any other future loss shape) now produces a loud `sys.exit(1)` naming the
id, never a silent `created <id>` for a ticket that does not exist.

Verified by FORCING the condition (never by filing tickets until one
fails):
1. Monkeypatched `commit_ticket_ledger_change` to return
   `Err(LeaseError.LandInProgress)` -- asserted `_new` exits 1 and NO
   `created ...` line is ever logged.
2. Monkeypatched a post-commit `load_all` to report the id absent (any
   other silent-loss seam, not just the one above) -- asserted the same:
   exit 1, no success line, human or `--json`.
3. Confirmed the ordinary, uncontended path is unaffected: the success
   line still prints (both human and `--json` forms), and by that point
   the ticket genuinely reads back from the store -- not mocked.

Orphaned-lock detection (the ticket's second ask): recommended as worth
surfacing routinely -- by construction a `.frob/tickets/<id>.lock` file
whose id has no corresponding ticket anywhere is exactly this failure
shape, and would have caught T-4313 within minutes. Filed as T-4342
rather than implemented here: its natural home is `frob.tickets._leases`
(alongside `orphaned_leases`/`release_orphaned_lease`), which is both
outside T-4339's declared scope and held by another in-flight agent
(T-4314) for the duration of this work.

SCOPE002 DISCLOSURE (same accepted precedent as T-3914/T-3930/T-4013/
T-4019/T-4132 for this exact shape): widening scope to cover
`src/frob/app/ticket_runner/_new.py` (the file the actual `_new` verb and
`created <id>` success line live in -- the ticket's own declared scope,
`src/frob/tickets/_create.py`, does not exist) pulls in every OTHER
function's PRE-EXISTING frob:doc/frob:tests closure edges in that file
(`_emit_scope_closure_warnings` -> docs/design/cli-hygiene.md,
`related_tickets` -> docs/modules/tickets.md, plus several PRE-EXISTING
frob:tests edges into tests/unit/test_app_runners_batch7.py,
tests/unit/test_new_ticket_scope_overlap_warning.py,
tests/unit/test_scope_closure_warning_collapse_t1556.py,
tests/unit/test_ticket_new_json.py, tests/unit/test_ticket_new_related.py,
tests/unit/test_ticket_new_scope_plausibility.py, plus two private-helper
SCOPE002 findings into src/frob/app/ticket_runner/__init__.py and
src/frob/app/ticket_runner/_verify.py) -- none of which this ticket
touches or changes.

frob:waive SCOPE002 reason="src/frob/app/ticket_runner/_new.py is the
whole `frob ticket new` command family in one module (its own top-of-file
LARGE001 waiver says so); T-4339 only touches `_new`/adds
`_confirm_new_ticket_readback_or_exit`, both new/changed code with no
frob:doc or frob:tests edges of their own yet (covered instead by the
new tests/unit/test_ticket_new_readback_guard_t4339.py, in scope and
cited as evidence). Every SCOPE002 finding here is a PRE-EXISTING edge on
a DIFFERENT function this ticket never modifies -- widening scope to
close them cascades into unrelated modules per the T-3914/T-3930/T-4013/
T-4019/T-4132 precedent for this identical shape."

Changed:
- src/frob/app/ticket_runner/_new.py::_new
- src/frob/app/ticket_runner/_new.py::_confirm_new_ticket_readback_or_exit (new)
- tests/unit/test_ticket_new_readback_guard_t4339.py (new)

Evidence:
- tests/unit/test_ticket_new_readback_guard_t4339.py::TestReadbackGuardForcesLoudFailure::test_land_in_progress_rollback_prints_no_success_line
- tests/unit/test_ticket_new_readback_guard_t4339.py::TestReadbackGuardForcesLoudFailure::test_readback_miss_after_reported_success_prints_no_success_line
- tests/unit/test_ticket_new_readback_guard_t4339.py::TestNormalPathStillCommitsAndReportsSuccess::test_ordinary_filing_prints_success_and_reads_back
- tests/unit/test_ticket_new_readback_guard_t4339.py::TestNormalPathStillCommitsAndReportsSuccess::test_json_path_still_reports_success_and_reads_back

Filed: T-4342 (Surface orphaned per-ticket lock files as a routine detection signal, out of scope for T-4339, natural home src/frob/tickets/_leases.py held by another in-flight agent)

Gates: `frob check --ticket T-4339` clean except:
- 3 pre-existing errors in docs/modules/verify-rapid-debt-visibility.md (DRIFT002/INV003/REF002), owned by T-4334, unrelated to this ticket's diff
- SCOPE002 findings on src/frob/app/ticket_runner/_new.py, waived above (pre-existing edges on functions this ticket does not touch)

### Changed
```
 tickets/T-4339/ticket.md | 20 ++++++++++++++++++++
 1 file changed, 20 insertions(+)
```

### Evidence
- `tests/unit/test_ticket_new_readback_guard_t4339.py::TestReadbackGuardForcesLoudFailure::test_land_in_progress_rollback_prints_no_success_line` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_new_readback_guard_t4339.py::TestReadbackGuardForcesLoudFailure::test_readback_miss_after_reported_success_prints_no_success_line` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_new_readback_guard_t4339.py::TestNormalPathStillCommitsAndReportsSuccess::test_ordinary_filing_prints_success_and_reads_back` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_new_readback_guard_t4339.py::TestNormalPathStillCommitsAndReportsSuccess::test_json_path_still_reports_success_and_reads_back` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 4 error(s), 4707 warning(s), 955 waived
- error-findings: DRIFT002@docs/guides/agent-playbook-appendix.md, INV003@docs/modules/verify-rapid-debt-visibility.md, REF002@docs/modules/verify-rapid-debt-visibility.md, SCOPE002@tickets.md
