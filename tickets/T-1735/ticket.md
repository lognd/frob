---
id: T-1735
title: SYS108 missing from _KNOWN_GATE_RULES, self-model node count drift (23 vs 22)
state: done
kind: bug
origin: human
created: '2026-08-07'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_rule_id_scan.py
- tests/test_gates.py
- src/frob/strata/_selfconform.py
- tests/system/test_frob_self_model.py
- tickets/T-1735/ticket.md
- tickets/T-1773/ticket.md
- tickets/T-1735/done-report.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tickets/T-1735/ticket.md
  reason: v2 ledger per-ticket files; T-1773 dropped as absorbed-by T-1800 from this
    same worktree session
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tickets/T-1773/ticket.md
  reason: v2 ledger per-ticket files; T-1773 dropped as absorbed-by T-1800 from this
    same worktree session
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tickets/T-1735/done-report.md
  reason: v2 ledger per-ticket done-report file
  actor: logan
  at: '2026-08-08'
evidence:
- tests/system/test_frob_self_model.py::TestFrobSelfModel::test_parses_and_elaborates
- tests/test_gates.py::TestKnownGateRuleIds::test_every_emitted_rule_literal_is_known
designated_repro_test: null
threat: null
component: null
---
Observed 2026-08-07 running `frob test --base main` after merging main into a
long-running worktree (T-1587's own worktree, unrelated to this defect).

Two test failures, both pre-existing on main and unrelated to my own diff
(`src/frob/tickets/_store.py`/`_reporting.py`/`tests/unit/test_ticket_store.py`/
`docs/design/ledger-v2.md`):

- `tests/test_gates.py::TestKnownGateRuleIds::test_every_emitted_rule_literal_is_known`
  fails: `SYS108` (`src/frob/strata/_selfconform.py:1407`) is constructed but
  missing from `_KNOWN_GATE_RULES`.
- `tests/system/test_frob_self_model.py::TestFrobSelfModel::test_parses_and_elaborates`
  fails: `assert 23 == 22` (module node count drift, same self-model area).

Confirmed neither failure references anything in my own scope by running the
two tests directly against the merged tree. Not investigated further --
filing so the drift is tracked rather than silently re-discovered by the
next agent who merges main.