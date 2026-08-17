---
id: T-2041
title: 'docs/modules/tickets.md: document T-2023''s land-wait budget config + start-relative
  scaling'
state: done
kind: docs
origin: agent
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- cmd:grep -n "Land-wait budget config and start-relative scaling" docs/modules/tickets.md
  exit=0 sha256=2b6b8f72a649
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-2023 added `_load_land_wait_timeout_s`, `_land_lock_started_at`, and
`_resolve_land_wait_budget` to `src/frob/tickets/_leases.py` (the land-wait
budget now scales to the in-flight land's own recorded start time, and is
configurable via `frob.toml`'s `[tickets] land_wait_timeout_s`), but could
not add `docs/modules/tickets.md` to scope -- T-2025 held a live write
lease on that file at the time. Add a short note to
`docs/modules/tickets.md#land-exclusivity-lease-t-1619` documenting the
new config key and the land-start-relative wait scaling once the lease
clears.

## Done report

Re-measured before writing: docs/modules/tickets.md's Land exclusivity
lease section had no mention of _load_land_wait_timeout_s,
_land_lock_started_at, or _resolve_land_wait_budget on current main, so
the gap T-2023 left open was still real. Added a note documenting the
new frob.toml [tickets] land_wait_timeout_s config key (default 330s,
same as the existing _LAND_WAIT_TIMEOUT_S constant, confirmed by
reading the source) and the land-start-relative wait-budget scaling
(remaining budget = resolved_timeout - (now - started_at), floored at
zero), with frob:describes directives back to all three functions.

### Changed
```
 tickets/T-2003/done-report.md | 27 +++++++++++++++++++++++++++
 tickets/T-2003/ticket.md      |  5 ++++-
 tickets/T-2024/done-report.md | 31 +++++++++++++++++++++++++++++++
 tickets/T-2024/ticket.md      |  7 ++++++-
 tickets/T-2035/ticket.md      |  7 +++++--
 tickets/T-2041/ticket.md      |  5 ++++-
 6 files changed, 77 insertions(+), 5 deletions(-)
```

### Evidence
- `cmd:grep -n "Land-wait budget config and start-relative scaling" docs/modules/tickets.md exit=0 sha256=2b6b8f72a649` (cmd evidence, exit=0)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH001@src/frob/app/ticket_runner/_query.py, ARCH001@src/frob/app/ticket_runner/_rapid_sweep.py, ARCH001@src/frob/tickets/_land.py, ARCH103@src/frob/app/ticket_runner/_query.py, DOC005@README.md, DOC005@docs/modules/cli.md, E501@/home/logan/projects/frob/.claude/worktrees/t2003-series/src/frob/app/ticket_runner/_rapid_sweep.py, PERF004@src/frob/tickets/_land.py, PII012@src/frob/testing/_coverage_refresh.py
