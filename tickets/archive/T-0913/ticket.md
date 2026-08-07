---
id: T-0913
title: 'strata: graphlang node missing exec/net/fetch_url may declarations (SELFAUDIT001
  SYS100, from T-0625''s _logging_checks.py)'
state: dropped
kind: bug
origin: human
created: '2026-07-26'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
Found while working T-0845 (attr-forwarding surface for cache flows,
scope: src/frob/strata/**, design/frob.strata, tests/unit/strata/**).

`frob check` (SELFAUDIT gate) reports 4 SYS100 findings, pre-existing
and unrelated to T-0845's own change:

  [gate:SELFAUDIT] design:1  SELFAUDIT001  self-audit family SYS100
  node=graphlang: capability 'exec' observed at
  src/frob/arch/_logging_checks.py:67 but not declared
  node=graphlang: capability 'net' observed at
  src/frob/arch/_logging_checks.py:70 but not declared
  node=graphlang: capability 'net' observed at
  src/frob/arch/_logging_checks.py:71 but not declared
  node=graphlang: capability 'net' observed at
  src/frob/arch/_logging_checks.py:73 but not declared
  node=graphlang: capability 'fetch_url' observed but not declared

design/frob.strata's `graphlang` node (src/frob/graph/**,
src/frob/lang/**, src/frob/arch/**) currently declares only
`may "eval"`/`"fs"`/`"fs-read"`/`"sql"`. `src/frob/arch/_logging_checks.py`
(landed by T-0625's ARCH1xx dependency-cycle work, unrelated to T-0845)
apparently exercises real exec/net/fetch_url-shaped capability at those
line numbers -- either graphlang's `may` set needs `"exec"`/`"net"` added
(with the honest capability-observed rationale precedent other `may`
additions in this node's comment history already document), or the
scanner's match there is a false-positive needing the same T-0882-style
substring/self-match investigation applied to eval/exec elsewhere, or a
disposed `frob:waive` if genuinely benign. Not investigated further here
-- out of scope for T-0845's own REL200 attr-forwarding-surface work.

## Drop reason
- 2026-07-26: duplicate of T-0910 (same SELFAUDIT001 finding on _logging_checks.py/graphlang node, third independent filing; T-0910 is in-progress)