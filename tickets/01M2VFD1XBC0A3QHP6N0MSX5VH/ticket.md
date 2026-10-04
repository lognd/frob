+++
id = "01M2VFD1XBC0A3QHP6N0MSX5VH"
title = "Land-lock guard tests must hold the lock from a real foreign pid, not their own"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
reporter = "human"
created = "2026-09-19T00:00:00Z"
updated = "2026-09-19T00:00:02Z"
aliases = ["T-5035"]
labels = ["milestone:0.533.0"]
scope = ["tests/test_ticket_reconcile.py", "tests/test_tickets_parent.py", "tests/test_tickets_priority.py", "tests/unit/verify/test_drain.py"]

[[acceptance]]
text = "test_apply_refuses_and_writes_nothing_while_land_lock_held passes"
bound = false

[[acceptance]]
text = "TestSetParentLandInProgressGuard test_refuses_and_writes_nothing_while_land_lock_held passes"
bound = false

[[acceptance]]
text = "TestSetPriorityLandInProgressGuard test_refuses_and_writes_nothing_while_land_lock_held passes"
bound = false

[[acceptance]]
text = "test_excludes_its_own_originating_land_pid passes"
bound = false
+++

CI run 35476139324 on dev: 4 tests fail because src/frob/tickets/_leases.py's land-lock probing now excludes the CALLING PROCESS's own pid as a foreign land holder (a real, intentional self-pid-exclusion feature, kept as-is per design decision). All 4 tests simulate a held land lock via fcntl.flock from within the SAME test process, writing os.getpid() into the lock file as the 'holder' pid -- so the self-exclusion now (correctly, by the new design) treats their synthetic lock as self-held and no longer refuses/excludes it, when the test's intent is to simulate a FOREIGN land holder. Fix: each of the 4 tests must hold the lock from a genuinely separate process -- spawn a sleeping subprocess with sys.executable (e.g. python -c 'import time; time.sleep(N)') and flock the lock file from within it, write ITS pid (not the test process's own) into the lock JSON, then run the guard/probe under test and assert it still refuses/excludes as a real foreign land. Test-only change, no src edits. NOTE: all 4 files are currently leased by other in-progress tickets (T-4627: test_tickets_priority.py, T-4623: test_tickets_parent.py + test_ticket_reconcile.py, T-4782: test_drain.py) -- this ticket cannot start until those leases clear; block on them.
