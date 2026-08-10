---
id: T-1939
title: 'No rule-level telemetry: cannot measure which of 293 gate rules ever fire'
state: done
kind: feature
origin: human
created: '2026-08-09'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/telemetry/
- tests/unit/telemetry/**
- src/frob/check/_python.py
- docs/guides/agentic-time-profiling.md
- design/frob.strata
- docs/design/registry/capability-via-ratchet.lock.json
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/telemetry/**
  reason: tests for the new package belong in the ticket's scope; check/_python.py
    is the single call site where the gates-stage GateReport is available to hook
    rule-counts emission into
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/check/_python.py
  reason: tests for the new package belong in the ticket's scope; check/_python.py
    is the single call site where the gates-stage GateReport is available to hook
    rule-counts emission into
  actor: logan
  at: '2026-08-10'
- op: add
  glob: docs/guides/agentic-time-profiling.md
  reason: new module's frob:doc anchors live in this existing telemetry-docs page
    (added a new section rather than a new orphan doc file)
  actor: logan
  at: '2026-08-10'
- op: add
  glob: design/frob.strata
  reason: the new frob.telemetry node requires design/frob.strata registration (SYS102),
    and adding the testsuite fs.read via-list entry for the new test file requires
    bumping its ratchet ceiling in the same diff (SELFAUDIT001/SYS111)
  actor: logan
  at: '2026-08-10'
- op: add
  glob: docs/design/registry/capability-via-ratchet.lock.json
  reason: the new frob.telemetry node requires design/frob.strata registration (SYS102),
    and adding the testsuite fs.read via-list entry for the new test file requires
    bumping its ratchet ceiling in the same diff (SELFAUDIT001/SYS111)
  actor: logan
  at: '2026-08-10'
evidence:
- tests/unit/telemetry/test_rule_counts.py::TestRuleFiringCounts::test_counts_kept_violations
- tests/unit/telemetry/test_rule_counts.py::TestRuleFiringCounts::test_waived_violations_still_count_as_fired
- tests/unit/telemetry/test_rule_counts.py::TestRuleFiringCounts::test_kept_and_waived_of_the_same_rule_combine
- tests/unit/telemetry/test_rule_counts.py::TestRuleFiringCounts::test_empty_report_produces_an_empty_map
- tests/unit/telemetry/test_rule_counts.py::TestRecordRuleFiringCounts::test_appends_one_event_with_every_fired_rule
- tests/unit/telemetry/test_rule_counts.py::TestRecordRuleFiringCounts::test_empty_report_appends_a_zero_rule_event
- tests/unit/telemetry/test_rule_counts.py::TestRecordRuleFiringCounts::test_respects_no_telemetry_opt_out
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
AUDIT FINDING (full gate audit, 2026-08-09).

The question "which of our 293 gate rules earn their keep?" cannot be
answered from recorded data. `.frob/telemetry.jsonl` (36,982 records,
8.6MB) has exactly two record shapes:

  ('args_head','duration_ms','exit','iso_ts','kind','subcommand','tree_hash')
  ('event','iso_ts','kind','ticket_id')

Zero records carry a rule dimension -- distinct rule ids in telemetry: 0.
So we record how long `frob check` TOOK and whether it PASSED, but never
which rules fired, how often, or how long each cost.

CONSEQUENCE: this audit had to proxy rule liveness by grepping the ticket
ledger for rule-id mentions. That proxy is biased in a way that matters --
it measures rules that caused ARGUMENT, not rules that caused WORK. A
rule that fires constantly and is fixed without comment looks identical
to a rule that never fires at all.

VALUE: rule-level firing counts would make three recurring decisions
mechanical instead of speculative -- retiring a rule that never fires,
finding the slowest rule when check time regresses, and identifying which
rules actually gate a given subsystem. It also gives the ratchet a real
denominator.

Prefer emitting this automatically from the existing gate-result path
(the findings already exist in memory at the end of every check; only the
write is missing) over adding a `frob gates stats` verb the operator must
know to run. Surfacing belongs where people already look.

## Done report

Built `frob.telemetry` (new package): one cheap, always-on JSONL telemetry
event per real `frob check` gates-stage run, carrying `rule -> total-fired
count` over every rule that fired at least once this run (kept violation
OR waived -- a waived rule still fired). Closes the audit finding that
`.frob/telemetry.jsonl` records duration/pass-fail but zero rule dimension,
so "which of our ~293 gate rules ever fire" could only be answered by a
biased ticket-ledger-mention proxy.

Changed:
- src/frob/telemetry/__init__.py (new) -- `rule_firing_counts(report)`
  (pure counting pass over `GateReport.violations`/`.waived`) and
  `record_rule_firing_counts(root, report)` (appends one
  `kind="gate_rule_counts"` event via the EXISTING
  `frob.app.telemetry.append_event` writer -- same file, same
  `FROB_NO_TELEMETRY` opt-out, no second write mechanism).
- src/frob/check/_python.py::_run_gates -- calls
  `record_rule_firing_counts(root, result.danger_ok)` right after a
  successful `run_gates()` call, the one place the gates-stage
  `GateReport` already exists in memory. Per this ticket's own explicit
  design directive ("surface automatically... not behind a command
  name"), no new CLI verb.
- docs/guides/agentic-time-profiling.md -- new "Rule-level gate firing
  counts (T-1939)" section (this module's `frob:doc` target), added
  beside the existing `.frob/telemetry.jsonl` documentation rather than a
  new orphan doc page.
- design/frob.strata -- new `node telemetry` (SYS102 self-conformance
  requires every `src/` package have a `code=`-bound node; this one
  declares no fs/env/exec capability of its own since it delegates the
  actual write to `frob.app.telemetry.append_event`, already covered by
  that module's own node).
- docs/design/registry/capability-via-ratchet.lock.json -- bumped
  `testsuite::fs.read` 123 -> 124 for the new test file's own
  `.read_text()` verification of the appended JSONL line (a real,
  disclosed new capability site, same pattern T-1943 hit for
  `_vet_examined_sites` earlier in this series).

Evidence: 7 pytest node ids in tests/unit/telemetry/test_rule_counts.py
(4 for `rule_firing_counts`'s pure-counting contract, 3 for
`record_rule_firing_counts`'s append/opt-out behavior). Also ran
tests/test_check_runner.py (unaffected, 20/20 combined pass) to confirm
the new call site in `_run_gates` did not disturb the existing
gates-stage wiring.

Gates: frob check --only gates --ticket T-1939 -- 4 errors remain, NONE
of them this ticket's: 2x ARCH001 in src/frob/gates/_fix_engine_sync.py
(pre-existing residue of T-2001, already being handled as T-2013 per
coordinator instruction -- confirmed not touched by this diff), 1x COV003
on T-0907's own evidence (pre-existing, unrelated file), 1x SCOPE001 on
tickets/T-1959/ticket.md (this worktree's own T-1959 fail-attempt ledger
entry, auto-committed by `frob ticket fail`, outside T-1939's declared
scope by construction -- same benign pattern the T-1943/T-1965 lands in
this series already hit and resolved at land). 220 SCOPE002 warnings
remain against design/frob.strata's pre-existing doc-closure gap
(docs/strata/roadmap.md) -- same class of hub-file closure debt already
filed as T-2012 in this series, not re-filed here.

Filed: none new (T-2012, filed earlier in this series, already covers
the general class of hub-doc SCOPE002 closure debt this ticket's
design/frob.strata touch also surfaced).

### Changed
```
 design/frob.strata                                 |  18 +++-
 .../registry/capability-via-ratchet.lock.json      |   6 +-
 docs/guides/agentic-time-profiling.md              |  29 +++++
 src/frob/check/_python.py                          |   7 ++
 src/frob/telemetry/__init__.py                     | 117 +++++++++++++++++++++
 tests/unit/telemetry/__init__.py                   |   0
 tests/unit/telemetry/test_rule_counts.py           | 113 ++++++++++++++++++++
 tickets/T-1939/ticket.md                           |  50 ++++++++-
 tickets/T-1959/ticket.md                           |   1 +
 9 files changed, 336 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/unit/telemetry/test_rule_counts.py::TestRuleFiringCounts::test_counts_kept_violations` (pytest node id, verified passing when recorded)
- `tests/unit/telemetry/test_rule_counts.py::TestRuleFiringCounts::test_waived_violations_still_count_as_fired` (pytest node id, verified passing when recorded)
- `tests/unit/telemetry/test_rule_counts.py::TestRuleFiringCounts::test_kept_and_waived_of_the_same_rule_combine` (pytest node id, verified passing when recorded)
- `tests/unit/telemetry/test_rule_counts.py::TestRuleFiringCounts::test_empty_report_produces_an_empty_map` (pytest node id, verified passing when recorded)
- `tests/unit/telemetry/test_rule_counts.py::TestRecordRuleFiringCounts::test_appends_one_event_with_every_fired_rule` (pytest node id, verified passing when recorded)
- `tests/unit/telemetry/test_rule_counts.py::TestRecordRuleFiringCounts::test_empty_report_appends_a_zero_rule_event` (pytest node id, verified passing when recorded)
- `tests/unit/telemetry/test_rule_counts.py::TestRecordRuleFiringCounts::test_respects_no_telemetry_opt_out` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH001@src/frob/gates/_fix_engine_sync.py, COV003@tickets/T-0907, F401@/home/logan/projects/frob/.claude/worktrees/coverage-family-series/tests/test_gates_fmt_directives.py, F401@/home/logan/projects/frob/.claude/worktrees/coverage-family-series/tests/unit/test_tickets_evidence_only_scope.py
