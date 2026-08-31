---
id: T-3483
title: INV/NEGEXIST/WALK/DEAD/LANG WARN gate remainder after T-2368's PLACE001/PII011
  close
state: done
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
scope:
- src/frob/gates/_docstatus.py
- src/frob/gates/_gate_cache.py
- src/frob/lang/_support.py
- src/frob/refactor/_prose.py
- src/frob/tickets/_models.py
- src/frob/app/ticket_runner/_new.py
- src/frob/clean/_core.py
- src/frob/gates/_docblocks.py
- src/frob/gates/_rule_id_scan.py
- src/frob/cve/_parser.py
- src/frob/gates/_doclink_docanchor.py
- src/frob/vet/_lifecycle.py
- src/frob/vet/_source.py
- src/frob/graph/__init__.py
- src/frob/strata/_bootstrap.py
- src/frob/strata/_selfconform_kinds.py
- src/frob/strata/_shrink.py
- src/frob/testing/_collect.py
- src/frob/testing/_collect_cpp.py
- src/frob/testing/_collect_kotlin.py
- src/frob/testing/_collect_rust.py
- src/frob/testing/_collect_ts.py
- src/frob/tickets/_brief.py
- src/frob/tickets/_renumber_v2.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_docstatus.py
  reason: 'WALK001 burn-down: reviewed per-site, file(s) touched by the T-3483 WALK001
    remainder'
  actor: logan
  at: '2026-08-30'
- op: add
  glob: src/frob/gates/_gate_cache.py
  reason: 'WALK001 burn-down: reviewed per-site, file(s) touched by the T-3483 WALK001
    remainder'
  actor: logan
  at: '2026-08-30'
- op: add
  glob: src/frob/lang/_support.py
  reason: 'WALK001 burn-down: reviewed per-site, file(s) touched by the T-3483 WALK001
    remainder'
  actor: logan
  at: '2026-08-30'
- op: add
  glob: src/frob/refactor/_prose.py
  reason: 'WALK001 burn-down: reviewed per-site, file(s) touched by the T-3483 WALK001
    remainder'
  actor: logan
  at: '2026-08-30'
- op: add
  glob: src/frob/tickets/_models.py
  reason: 'WALK001 burn-down: reviewed per-site, file(s) touched by the T-3483 WALK001
    remainder'
  actor: logan
  at: '2026-08-30'
- op: add
  glob: src/frob/app/ticket_runner/_new.py
  reason: 'WALK001 burn-down: reviewed per-site, file(s) touched by the T-3483 WALK001
    remainder'
  actor: logan
  at: '2026-08-30'
- op: add
  glob: src/frob/clean/_core.py
  reason: 'WALK001 burn-down: reviewed per-site, file(s) touched by the T-3483 WALK001
    remainder'
  actor: logan
  at: '2026-08-30'
- op: add
  glob: src/frob/gates/_docblocks.py
  reason: 'WALK001 burn-down: reviewed per-site, file(s) touched by the T-3483 WALK001
    remainder'
  actor: logan
  at: '2026-08-30'
- op: add
  glob: src/frob/gates/_rule_id_scan.py
  reason: 'WALK001 burn-down: reviewed per-site, file(s) touched by the T-3483 WALK001
    remainder'
  actor: logan
  at: '2026-08-30'
- op: add
  glob: src/frob/cve/_parser.py
  reason: 'WALK001 burn-down: reviewed per-site, file(s) touched by the T-3483 WALK001
    remainder'
  actor: logan
  at: '2026-08-30'
- op: add
  glob: src/frob/gates/_doclink_docanchor.py
  reason: 'WALK001 burn-down: reviewed per-site, file(s) touched by the T-3483 WALK001
    remainder'
  actor: logan
  at: '2026-08-30'
- op: add
  glob: src/frob/vet/_lifecycle.py
  reason: 'WALK001 burn-down: reviewed per-site, file(s) touched by the T-3483 WALK001
    remainder'
  actor: logan
  at: '2026-08-30'
- op: add
  glob: src/frob/vet/_source.py
  reason: 'WALK001 burn-down: reviewed per-site, file(s) touched by the T-3483 WALK001
    remainder'
  actor: logan
  at: '2026-08-30'
- op: add
  glob: src/frob/graph/__init__.py
  reason: 'WALK001 burn-down: reviewed per-site, file(s) touched by the T-3483 WALK001
    remainder'
  actor: logan
  at: '2026-08-30'
- op: add
  glob: src/frob/strata/_bootstrap.py
  reason: 'WALK001 burn-down: reviewed per-site, file(s) touched by the T-3483 WALK001
    remainder'
  actor: logan
  at: '2026-08-30'
- op: add
  glob: src/frob/strata/_selfconform_kinds.py
  reason: 'WALK001 burn-down: reviewed per-site, file(s) touched by the T-3483 WALK001
    remainder'
  actor: logan
  at: '2026-08-30'
- op: add
  glob: src/frob/strata/_shrink.py
  reason: 'WALK001 burn-down: reviewed per-site, file(s) touched by the T-3483 WALK001
    remainder'
  actor: logan
  at: '2026-08-30'
- op: add
  glob: src/frob/testing/_collect.py
  reason: 'WALK001 burn-down: reviewed per-site, file(s) touched by the T-3483 WALK001
    remainder'
  actor: logan
  at: '2026-08-30'
- op: add
  glob: src/frob/testing/_collect_cpp.py
  reason: 'WALK001 burn-down: reviewed per-site, file(s) touched by the T-3483 WALK001
    remainder'
  actor: logan
  at: '2026-08-30'
- op: add
  glob: src/frob/testing/_collect_kotlin.py
  reason: 'WALK001 burn-down: reviewed per-site, file(s) touched by the T-3483 WALK001
    remainder'
  actor: logan
  at: '2026-08-30'
- op: add
  glob: src/frob/testing/_collect_rust.py
  reason: 'WALK001 burn-down: reviewed per-site, file(s) touched by the T-3483 WALK001
    remainder'
  actor: logan
  at: '2026-08-30'
- op: add
  glob: src/frob/testing/_collect_ts.py
  reason: 'WALK001 burn-down: reviewed per-site, file(s) touched by the T-3483 WALK001
    remainder'
  actor: logan
  at: '2026-08-30'
- op: add
  glob: src/frob/tickets/_brief.py
  reason: 'WALK001 burn-down: reviewed per-site, file(s) touched by the T-3483 WALK001
    remainder'
  actor: logan
  at: '2026-08-30'
- op: add
  glob: src/frob/tickets/_renumber_v2.py
  reason: 'WALK001 burn-down: reviewed per-site, file(s) touched by the T-3483 WALK001
    remainder'
  actor: logan
  at: '2026-08-30'
evidence:
- tests/test_walk_lint_gate.py::TestBoundedScopeWaiver::test_waived_bounded_glob_is_suppressed_end_to_end
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 7c83b1fbd9a97ddea5a90cc77015a84ac7515ae1
---
T-2368 closed PLACE001 (2 findings fixed, directive placement) and promoted PLACE001/PII011 WARN -> ERROR (both at genuine zero unwaived findings). The remaining codes in T-2368's original family are NOT fixed and NOT promoted -- their counts have grown since T-2368's own 2026-08-18 measurement. Re-measured 2026-08-30 via uv run frob check --json --budget 500:

WALK001: 36 (was 3 at T-2368 file time)
DEAD001: 31 (was 5)
NEGEXIST001: 17 (was 13)
INV003: 12 (was part of 10 combined with INV004)
INV004: 12
LANG003: 12 (was 3)

Each of these needs the same per-finding review T-2368's own body called for (read docs/modules/gates.md per code, do not assume a shared fix) before promoting; none of that review happened in T-2368's own pass -- it stopped at the two cheap PLACE001/PII011 wins. Do not blanket-waive to reach zero. Narrow scope to the actual touched files once picked up.