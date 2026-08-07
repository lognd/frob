---
id: T-1726
title: Fix ARCH001/ARCH103/SEC110 drift in _coverage_refresh.py from T-1677
state: dropped
kind: bug
origin: human
created: '2026-08-07'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/testing/_coverage_refresh.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
T-1677 (frob coverage watchdog) landed new code in
`src/frob/testing/_coverage_refresh.py` that trips gate errors on main,
outside T-1685's declared scope:

- ARCH001: `_spawn_with_watchdog` has 102 lines (threshold 60)
- ARCH001: `_pytest_outcome` has 84 lines (threshold 60)
- ARCH103: `_kill_process_group` mixes I/O, string-formatting, and 2
  decision points in one body
- ARCH103: `_spawn_with_watchdog` mixes I/O, string-formatting, and 6
  decision points in one body
- SEC110: `_coverage_refresh.py:199` reads `os.environ.get(...)` with no
  declared std.secrets node or waiver

Found while verifying `frob check --land-parity` for T-1685 (main's
3-error floor). These 5 findings are unrelated to T-1685's scope
(tests/test_ticket_work_and_land_finish.py,
src/frob/tickets/_evidence.py,
docs/audits/docs-completeness-2026-08-06.md) and were not part of the
3-error floor T-1685 was scoped to clear -- they are new drift from a
separate, already-landed ticket. Split the two oversized functions along
an existing boundary the way this module's siblings already do, and
either map the env-var read to a declared std.secrets node or add a
reasoned SEC110 waiver.

## Drop reason
- 2026-08-07: duplicate: the deferred post-land sweep auto-filed T-1723 for the identical 3 errors in _coverage_refresh.py from T-1677's land, before this hand-filed one. Keeping the auto-filed record as canonical since it carries the sweep's own attribution to the introducing commit (absorbed by T-1723)