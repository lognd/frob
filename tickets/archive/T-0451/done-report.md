## Done report

Added `group` and `sudoers` to the clause-keywords regex alternation in
editors/vscode-strata/syntaxes/strata.tmLanguage.json (alphabetically
ordered, matching convention), so the vscode-strata grammar highlights the
clauses T-0272 added to strata-core/src/parse.rs. The one known-red test
(tests/unit/test_strata_tmlanguage.py::test_clause_keywords_covered_by_grammar,
missing_from_grammar was {'group','sudoers'}) now passes.

Evidence: test_clause_keywords_covered_by_grammar. Grammar-JSON-only change.

Note (real doable-collision, motivates T-0453): this ticket was picked and
completed by the easy-wins sweeper, but the coordinator ALSO dispatched a
dedicated T-0451 agent moments later because `frob ticket doable` did not
account for the sweeper's in-flight lease on it -- the duplicate was
redirected. Landed via 3-way.
