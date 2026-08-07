## Done report

Adds DOC010 (gate-gap class 4, non-python doc targets) to
frob.gates._doclink_docanchor.docmake_gate: every backtick-quoted
`make <target>` citation in an obligated/root/frob:doc-linked doc must
name a real Makefile recipe (a `<target>:` line, `.PHONY`/pattern/
variable-assignment lines excluded). No Makefile at all is a no-op, not
an error. Verified 0 real violations against this repo's own 124 obligated
docs -- every existing `make X` citation already resolves.

Scoped this portion narrowly to the Makefile-recipe half of gate-gap
class 4; DOC006's existing kind-3 (config reference) already resolves
`[section]`/`[section.key]` against frob.toml/pyproject.toml/Cargo.toml,
and kind-6 already resolves rust file/symbol citations -- both pre-date
this ticket and needed no new work. Cross-referenced T-1193 (the
python-only doc-graph theme this ticket's plan named) and confirmed no
overlap: T-1193's children are pure-python symbol/module pointer work,
untouched by the Makefile-target check landed here.

Wired docmake into frob.gates (_ALL_GATES, _CANONICAL_GATE_ORDER,
run_gates' dispatch table, __all__) and frob.check's gates-fast stage
group, alongside doclink/docanchor/docstatus. Registered DOC010 in
_KNOWN_GATE_RULES (waivable), a docs/modules/gates.md table row, and one
new CHK-GATE-DOC010 registry entry with gate_rule_total bumped 278 -> 279.

### Changed
```
 docs/audits/README.md                            |   2 +
 docs/audits/check-performance.md                 |   2 +
 docs/audits/coordination-churn.md                |   2 +
 docs/audits/docs-staleness-2026-07-29.md         |   2 +
 docs/audits/frob-blindspots-2026-07-23.md        |   2 +
 docs/audits/gates-accounting.md                  |   2 +
 docs/audits/gates-quality.md                     |   2 +
 docs/audits/gates-vacuous.md                     |   2 +
 docs/audits/graph.md                             |   2 +
 docs/audits/lang-check-docs.md                   |   2 +
 docs/audits/perf.md                              |   2 +
 docs/audits/strata.md                            |   2 +
 docs/audits/test005-zero-classification-t1418.md |   2 +
 docs/audits/tickets-testing-round2.md            |   2 +
 docs/audits/tickets-testing.md                   |   2 +
 docs/audits/vet.md                               |   2 +
 docs/design/registry/check-coverage.yaml         |  10 +-
 docs/modules/gates.md                            |   2 +
 src/frob/check/__init__.py                       |   1 +
 src/frob/gates/__init__.py                       |   8 +
 src/frob/gates/_doclink_docanchor.py             | 199 +++++++++++++-
 src/frob/gates/_waive.py                         |   4 +
 tests/test_gates.py                              | 113 ++++++++
 tickets.md                                       | 335 ++++++++++++++++++++++-
 24 files changed, 696 insertions(+), 8 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 4 error(s), 1057 warning(s), 745 waived
- error-findings: PERF002@src/frob/gates/_doclink_docanchor.py, PRE001@tickets/T-1230, SELFAUDIT001@design, WIRE001@src/frob/gates/_doclink_docanchor.py
