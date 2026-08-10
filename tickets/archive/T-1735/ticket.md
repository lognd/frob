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

## Done report

T-1735 named two distinct findings under one title. The SYS108-missing
half was already fixed and landed by T-1800 (commit 4883f36a7) before
this worktree merged main -- confirmed clean via
`tests/test_gates.py::TestKnownGateRuleIds::test_every_emitted_rule_literal_is_known`
passing on the merged tree; no code change needed here. The sibling
duplicate ticket T-1773 (identical title, SYS108-only body) was dropped
from this same worktree session, `--absorbed-by T-1800`.

The second, still-live finding -- `tests/system/test_frob_self_model.py
::TestFrobSelfModel::test_parses_and_elaborates` asserting `len(_model.
nodes) == 22` against a design tree that now elaborates 23 -- was real,
pre-existing debt: T-1687 (durable commit-keyed verify queue) added
`node verify : trusted` to `design/frob.strata` without updating this
test's running node-count tally, the same "landed a node, missed the
self-model counter" shape T-1591/T-1329's own comments in this test
already document for their own additions. `verify` declares no `may`
capability and sits off the cli-dispatch/component-import graph the
`f_*` flows model, so flows(44)/boundaries(1)/claims(31) are unaffected
-- confirmed by reading the test's own elaboration log output before
editing. Bumped the assertion to 23 and added the same style of
dated docstring comment T-1591/T-1329 use, crediting T-1687/T-1735.

### Changed
```
 tickets/T-1735/ticket.md | 17 ++++++++++++++++-
 tickets/T-1773/ticket.md |  7 +++++--
 2 files changed, 21 insertions(+), 3 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 0 error(s), 1401 warning(s), 732 waived
- error-findings: none (measured, zero errors)
