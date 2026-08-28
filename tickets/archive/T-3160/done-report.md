## Done report

Measured against main directly: `ty check` reproduced the missing-argument
finding identically on main before this fix, and re-running it after
the fix on the touched file shows "All checks passed!". This is a
real, live finding caused by T-3152's signature change to
_process_start_age_s (pid, proc, uptime_s -> pid, proc, uptime_s,
clk_tck, switching from directory-mtime-based age to
/proc/<pid>/stat starttime-based age), not just a type-check
observation: the old 3-arg call at
tests/unit/test_coordinator_scripts.py:3160 is missing a REQUIRED
positional argument, so it raises TypeError at runtime, not merely a
static-analysis complaint -- confirmed by diffing the parent commit's
version of this call against every other (correct) call site in the
same file, all of which already pass uptime_s + clk_tck.

The ticket's own attribution recorded this as UNATTRIBUTED; it is in
fact directly attributable to T-3152 (the commit that changed this
function's signature) -- worth flagging to the coordinator as a
possible systematic gap in the attribution engine (also seen on T-3172/
SYS003 per the coordinator's own note), not something to fix in this
ticket's scope.

Fix: pass the fixture's own `uptime_s` (already computed for the
synthetic /proc/uptime file this test writes) and
`os.sysconf("SC_CLK_TCK")`, matching every other call site's pattern in
this file (test_coordinator_scripts.py:2871, :3084 area). Confirmed the
old call was also semantically wrong even before the arity mismatch:
time.time() (wall clock) was never meaningful against this test's
synthetic /proc/uptime fixture value of 10_000_000.0.

Filed: none (attribution-gap observation reported to coordinator directly,
not filed as a new ticket per instructions).

### Changed
```
 tests/unit/test_coordinator_scripts.py | 2 +-
 tickets/T-3160/ticket.md               | 2 ++
 2 files changed, 3 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_coordinator_scripts.py::TestOrphanedForkserverCountAgreesWithReap::test_old_no_ancestor_forkserver_agrees` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
