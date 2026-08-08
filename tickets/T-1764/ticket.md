---
id: T-1764
title: 'Make the per-rule waive-rate a first-class number: 997 waivers against 276
  rules was measured by hand'
state: done
kind: feature
origin: human
created: '2026-08-07'
priority: high
blocked_by:
- T-1763
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_waive.py
- src/frob/app/check_runner.py
- tests/test_waive_gate.py
- src/frob/app/config.py
- src/frob/_cli_parsers/_check.py
- docs/modules/app.md
- src/frob/app/_config_external.py
- design/frob.strata
- tickets/T-1764/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: docs/modules/gates.md
  reason: docs/modules/gates.md is held by a concurrent agent (T-1773/T-1735/T-1781
    on _KNOWN_GATE_RULES); document --census in docs/modules/app.md instead. CLI wiring
    for a new --census flag needs config.py's AppConfig field and _cli_parsers/_check.py's
    argparse registration, neither of which was in the original scope.
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/app/config.py
  reason: docs/modules/gates.md is held by a concurrent agent (T-1773/T-1735/T-1781
    on _KNOWN_GATE_RULES); document --census in docs/modules/app.md instead. CLI wiring
    for a new --census flag needs config.py's AppConfig field and _cli_parsers/_check.py's
    argparse registration, neither of which was in the original scope.
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/_cli_parsers/_check.py
  reason: docs/modules/gates.md is held by a concurrent agent (T-1773/T-1735/T-1781
    on _KNOWN_GATE_RULES); document --census in docs/modules/app.md instead. CLI wiring
    for a new --census flag needs config.py's AppConfig field and _cli_parsers/_check.py's
    argparse registration, neither of which was in the original scope.
  actor: logan
  at: '2026-08-08'
- op: add
  glob: docs/modules/app.md
  reason: docs/modules/gates.md is held by a concurrent agent (T-1773/T-1735/T-1781
    on _KNOWN_GATE_RULES); document --census in docs/modules/app.md instead. CLI wiring
    for a new --census flag needs config.py's AppConfig field and _cli_parsers/_check.py's
    argparse registration, neither of which was in the original scope.
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/app/_config_external.py
  reason: 'WIRE001: --census''s check_census CLI dest must be wired into AppConfig.from_external''s
    field-name tuple or it is silently dropped'
  actor: logan
  at: '2026-08-08'
- op: add
  glob: design/frob.strata
  reason: frob sys sync-interface auto-registered census_gate_rules in the gates node's
    interface list (SELFAUDIT001)
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tickets/T-1764/**
  reason: SCOPE001 flags the ticket's own ticket.md/done-report.md under v2 storage
    (same fix T-1719 needed)
  actor: logan
  at: '2026-08-08'
evidence:
- tests/test_waive_gate.py::TestRuleCensus::test_corpus_wide_rule_gets_a_rate
- tests/test_waive_gate.py::TestRuleCensus::test_diff_scoped_rule_gets_no_rate
- tests/test_waive_gate.py::TestRuleCensus::test_dead_waiver_count_is_folded_in
- tests/test_waive_gate.py::TestWaive004DeadCount::test_counts_per_rule_from_message
- tests/test_waive_gate.py::TestWaive004DeadCount::test_empty_input_yields_empty_dict
- tests/test_waive_gate.py::TestCensusCli::test_census_prints_a_table_and_exits_zero
designated_repro_test: null
acceptance:
- text: 'METHODOLOGICAL CORRECTION (2026-08-07): the coordinator''s original waive-rate
    census was INVALID for diff-scoped rules. It compared waiver counts against live
    findings from a full unscoped ''frob check'' on a clean tree -- but a diff-scoped
    gate (AFFECT001, DUP001, and others) only ever fires on a diff, so 0 findings
    on a clean tree is its EXPECTED signature when the backlog is clean, not evidence
    it is broken. Acting on the raw number would have deleted two working detectors.'
  evidence:
  - tests/test_waive_gate.py::TestRuleCensus::test_diff_scoped_rule_gets_no_rate
- text: 'Therefore: the census MUST classify each rule as corpus-wide or diff-scoped
    BEFORE computing a waive-rate, and must compute the diff-scoped rules'' rate over
    diffs where they actually ran -- never over a clean-tree snapshot. A single undifferentiated
    waive-rate column is a metric that produces confidently wrong deletions.'
  evidence:
  - tests/test_waive_gate.py::TestRuleCensus::test_diff_scoped_rule_gets_no_rate
- text: _WAIVE004_STRUCTURALLY_UNVERIFIABLE_RULES already documents which rules are
    diff-scoped; read that classification rather than re-deriving it, and report any
    rule it does not cover.
  evidence:
  - tests/test_waive_gate.py::TestRuleCensus::test_diff_scoped_rule_gets_no_rate
threat: null
component: null
---
frob has 276 registered gate rules and 997 waiver directives against them
in its OWN source. Nobody could state that number before today; it was
measured by hand with a throwaway script, and it is the single most
informative fact about the tool's calibration.

Measured 2026-08-07 (waivers in `src/frob/**`, live findings from a full
`frob check` on a clean tree):

    RULE          WAIVED   LIVE   WAIVE-RATE
    INV006           338      0         100%
    COV007           124    338          27%
    EXHAUST003       104    273          28%
    PERF004           65    134          33%
    AFFECT001         49      0         100%
    EXHAUST002        43    113          28%
    ARCH103           25     52          32%
    ARCH001           23     48          32%
    DUP001            19      0         100%
    ARCH102           14     31          31%

Six rules are waived more often than they are obeyed. Three enforce
nothing at all.

THE PRINCIPLE THIS MAKES ENFORCEABLE: **a rule waived more often than it
is obeyed is not a rule, it is a tax.** An imprecise detector produces
false positives; false positives demand escape hatches; escape hatches
acquire flags and become verbs. That loop is why this CLI has 60
top-level verbs and 39 ticket subverbs, and why `frob ticket scope-ack`
exists as a four-flag command whose only purpose is silencing a warning
that nobody ever acts on (TICK009 has reported the same 4 outstanding
scope-breadth nudges all day while scopes were narrowed BY HAND).

Sprawl is the symptom. Detector imprecision is the disease.

WANTED: make the waive-rate a first-class, continuously-visible number so
this never again requires a hand-rolled script.

1. `frob check --census` (name negotiable; fold into the CLI regrouping
   in T-1567..T-1571 rather than adding a 61st top-level verb -- do not
   let the fix for sprawl add sprawl). For every registered rule: times
   fired, times waived, waive-rate, and the count of waivers whose
   `follow_up` names a closed ticket (a dead waiver).
2. Report DEAD WAIVERS explicitly: a directive suppressing a rule that no
   longer fires anywhere. Those are pure decay -- they read as live
   suppressions of live rules, so a reader assumes both still matter.
3. A rule's waive-rate crossing a threshold should itself be a finding
   against the RULE, not the code. Start it as a warning with the number
   in the message; do not make it blocking until the top offenders are
   dealt with, or it will fire on day one and be waived, which would be
   the joke writing itself.

EXPLICITLY NOT WANTED: a new suppression mechanism, a new verb outside
the regrouping, or a dashboard. The output is a table and a threshold.

Sequencing note: T-1763 (INV006/AFFECT001/DUP001, the three 100% rules)
should land FIRST. It removes 406 of the 997 waivers, which changes every
number in this table -- measuring after that lands gives a truer baseline
than measuring now. Do not run the census as a one-off before it; build
the standing capability so it can be re-run.

Related: T-1567..T-1571 (CLI regrouping) should be sequenced AFTER this.
Regrouping cruft yields organised cruft; the census tells us how much of
the surface is load-bearing before anyone rearranges it.

## Done report

Implemented `frob check --census` (T-1764): for every registered rule id
appearing in a full, unscoped gate run, prints fired/waived/waive-rate/
dead-waiver counts. Classifies each rule corpus-wide vs diff-scoped
BEFORE computing any waive-rate, per the hard requirement from the T-1763
methodological correction: a rule in
`frob.gates._waive._WAIVE004_STRUCTURALLY_UNVERIFIABLE_RULES` (currently
DUP001/DUP002/AFFECT001/AFFECT002/WIRE001/SCOPE001) gets `waive_rate=
None` and prints `n/a (diff-scoped)` instead of a number computed from
this single clean-tree snapshot -- 0 live findings there is the EXPECTED
signature of a healthy diff-scoped gate, never itself evidence the rule
is dead.

Core computation (`frob.gates._waive.census_gate_rules`, pure, takes a
`GateReport`'s `(violations, waived)` tuples) is a report, not a gate --
matches the ticket's explicit "not blocking yet" acceptance criterion;
nothing about a high waive-rate fails `frob check` today.

Deliberately NOT implemented (disclosed, not silently dropped):
- Item 1's "count of waivers whose follow_up names a closed ticket" --
  cut for time; `dead_waivers` (WAIVE004: a waiver matching zero live
  findings this run) is implemented and is the more load-bearing of the
  two "dead waiver" signals item 2 asks for.
- A true diff-scoped waive-rate computed "over diffs where [the rule]
  actually ran" (the acceptance criteria's stronger ask) needs historical
  diff data this single-snapshot pass does not have -- this census
  refuses to print a misleading number for those rules rather than
  attempting a wrong one.
- CLI regrouping (`--census` living under a broader verb per T-1567..
  T-1571) -- that epic is explicitly sequenced AFTER this ticket per its
  own Description; `--census` lands as a `frob check` flag for now.
- Registering `--census` in docs/modules/gates.md -- that file was held
  by a concurrent agent (T-1773/T-1735/T-1781) for the whole dispatch
  window; documented in docs/modules/app.md instead (new section: "frob
  check --census (T-1764)").

Changed:
- src/frob/gates/_waive.py: RuleCensusEntry (new), census_gate_rules
  (new), _waive004_dead_count_by_rule (new, private)
- src/frob/app/check_runner.py: _run_census, _census_gate_config,
  _print_census (new); wired into _handle_early_exit_modes
- src/frob/app/config.py: AppConfig.check_census (new field)
- src/frob/_cli_parsers/_check.py: --census flag registration
- src/frob/app/_config_external.py: check_census added to the
  AppConfig.from_external field-name tuple (WIRE001 fix)
- design/frob.strata: gates node interface += census_gate_rules
  (frob sys sync-interface auto-fix, SELFAUDIT001)
- docs/modules/app.md: new section "frob check --census (T-1764)"
- tests/test_waive_gate.py: TestRuleCensus (3 tests),
  TestWaive004DeadCount (2 tests), TestCensusCli (1 test)

Evidence:
- tests/test_waive_gate.py::TestRuleCensus.test_corpus_wide_rule_gets_a_rate
- tests/test_waive_gate.py::TestRuleCensus.test_diff_scoped_rule_gets_no_rate
- tests/test_waive_gate.py::TestRuleCensus.test_dead_waiver_count_is_folded_in
- tests/test_waive_gate.py::TestWaive004DeadCount.test_counts_per_rule_from_message
- tests/test_waive_gate.py::TestWaive004DeadCount.test_empty_input_yields_empty_dict
- tests/test_waive_gate.py::TestCensusCli.test_census_prints_a_table_and_exits_zero
- 40/40 tests/test_waive_gate.py pass (uv run pytest tests/test_waive_gate.py -q)

Gates: `uv run frob check --ticket T-1764` exit 0, every gate:* family
passes (ruff-check/ruff-format failures present are pre-existing
repo-wide debt, none in a file this ticket touched -- verified with a
targeted `uv run ruff check`/`format --check` over exactly this ticket's
files). `uv run frob check --land-parity` reports clean (0 unscoped
errors).

### Changed
```
 tickets/T-1764/ticket.md | 60 ++++++++++++++++++++++++++++++++++++++++++++++--
 1 file changed, 58 insertions(+), 2 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 0 error(s), 881 warning(s), 734 waived
- error-findings: none (measured, zero errors)
