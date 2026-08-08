## Done report

Implemented frob.gates._coverage._suspect_deflated_symbols: a per-symbol
deflation heuristic distinct from the existing aggregate
_module_join_fraction check. Flags a symbol whose defining line shows a
hit but every other body line in its span shows zero hits -- the
specific shape a partial xdist worker crash produces when the worker
was the sole source of data for just a handful of symbols, which does
not move the repo-wide join fraction enough for TEST017 to notice.

Per the ticket's own plan, corroboration is required before flagging: a
symbol is only a candidate if it has a frob:tests edge (checked on both
edge.src/edge.target, matching _evidence_binds_to_scope's own
either-direction convention in frob.gates). Without that expectation, a
genuinely dead/unexercised code path is indistinguishable from lost
worker data by the per-line shape alone, and a false positive here would
be worse than the problem, since TEST005/TEST011 already gate real work
on coverage signal -- this matches the ticket's explicit worry about
false positives.

Wired into load_coverage: when the heuristic fires, a WARNING is logged
naming every suspect symref (matching the existing pattern just above it
for the low-join-fraction case). This is NOT yet a gate Violation --
turning it into one needs a new rule id (e.g. TEST019) registered in
frob.gates._waive._KNOWN_GATE_RULES, a Violation-emitting function in
frob.gates.__init__.py (where every other CoverageData consumer lives),
and a docs/modules/gates.md section -- all three outside this ticket's
declared scope (src/frob/gates/_coverage.py, tests/test_gates.py).
docs/modules/gates.md was also under an active lease from another epic
at the time of this work per the dispatch brief's explicit warning.
Filed the follow-up: T-1877 (renumbers at land) "Wire T-1824's
per-symbol deflation heuristic into a real gate Violation (TEST019)".

Verified the corroboration requirement, the def-line/body-line shape
detection, the "no tests edge -> never flagged" false-positive guard,
and the "not enough lines to judge" no-verdict case all with synthetic
coverage.xml/graph-snapshot fixtures; also verified load_coverage's own
WARNING wiring end-to-end via caplog. All 5 new tests plus the full
pre-existing TestCoverageLoad suite (41 tests) pass together (46
collected, 0 failed).

frob check --land-parity: clean (0 unscoped errors) after this change.

### Changed
```
 src/frob/gates/_coverage.py        |  95 ++++++++++++++++++++++-
 tests/test_gates.py                | 154 +++++++++++++++++++++++++++++++++++++
 tickets/T-1824/ticket.md           |  10 ++-
 tickets/T-1877/ticket.md |  25 ++++++
 4 files changed, 282 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestSuspectDeflatedSymbols::test_def_line_hit_body_zero_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestSuspectDeflatedSymbols::test_genuinely_dead_code_not_flagged_without_tests_edge` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestSuspectDeflatedSymbols::test_uniformly_covered_symbol_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestSuspectDeflatedSymbols::test_single_line_symbol_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestSuspectDeflatedSymbols::test_load_coverage_logs_warning_for_suspect_symbol` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 1 error(s), 1295 warning(s), 743 waived
- error-findings: PRE001@tickets/T-1824
