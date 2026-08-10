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
