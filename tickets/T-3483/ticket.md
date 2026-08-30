---
id: T-3483
title: INV/NEGEXIST/WALK/DEAD/LANG WARN gate remainder after T-2368's PLACE001/PII011
  close
state: queued
kind: bug
origin: human
created: '2026-08-30'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-2368 closed PLACE001 (2 findings fixed, directive placement) and promoted PLACE001/PII011 WARN -> ERROR (both at genuine zero unwaived findings). The remaining codes in T-2368's original family are NOT fixed and NOT promoted -- their counts have grown since T-2368's own 2026-08-18 measurement. Re-measured 2026-08-30 via uv run frob check --json --budget 500:

WALK001: 36 (was 3 at T-2368 file time)
DEAD001: 31 (was 5)
NEGEXIST001: 17 (was 13)
INV003: 12 (was part of 10 combined with INV004)
INV004: 12
LANG003: 12 (was 3)

Each of these needs the same per-finding review T-2368's own body called for (read docs/modules/gates.md per code, do not assume a shared fix) before promoting; none of that review happened in T-2368's own pass -- it stopped at the two cheap PLACE001/PII011 wins. Do not blanket-waive to reach zero. Narrow scope to the actual touched files once picked up.