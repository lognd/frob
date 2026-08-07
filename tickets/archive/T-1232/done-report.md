## Done report

Adds DOC009 (gate-gap class 6, status/currency) to
frob.gates._doclink_docanchor.docstatus_gate: every docs/audits/*.md file
must carry a dated `Status: YYYY-MM-DD` header, or a `Status: SUPERSEDED
(see <path>)` header whose target actually resolves, within its first 15
lines. Missing header or a dangling superseded-by target is a DOC009
error. Retrofitted a status header onto all 16 pre-existing docs/audits/
files (dated from each file's last commit date via `git log`; the one
already-superseded doc, tickets-testing.md, got the SUPERSEDED form
pointing at tickets-testing-round2.md, matching its existing prose).

Wired docstatus into frob.gates (_ALL_GATES, _CANONICAL_GATE_ORDER,
run_gates' dispatch table, __all__) and frob.check's gates-fast stage
group, alongside doclink/docanchor. Registered DOC009 in
_KNOWN_GATE_RULES (waivable), a docs/modules/gates.md table row, and one
new CHK-GATE-DOC009 registry entry with gate_rule_total bumped 277 -> 278.

Left for follow-up (out of this portion, per the ticket's other two named
checks): ticket-id prose vs ledger state, and docs-tree index
completeness -- both need a real cross-reference against tickets.md/the
docs tree walk, a separate, larger mechanism than the header check this
lands. Filed T-1486 for those two (renumbers to a real T-#### at land),
rather than force them into this land.

### Changed
```
 docs/design/registry/check-coverage.yaml |   6 +-
 docs/modules/gates.md                    |   1 +
 src/frob/gates/_doclink_docanchor.py     | 125 +++++++++++++-
 src/frob/gates/_waive.py                 |   2 +
 tests/test_gates.py                      |  57 +++++++
 tickets.md                               | 285 ++++++++++++++++++++++++++++++-
 6 files changed, 469 insertions(+), 7 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 4 error(s), 823 warning(s), 745 waived
- error-findings: PERF002@src/frob/gates/_doclink_docanchor.py, PRE001@tickets/T-1232, SELFAUDIT001@design, WIRE001@src/frob/gates/_doclink_docanchor.py
