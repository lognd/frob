## Done report

Changed:
- docs/design/gate-semantics-classification.md (new)

Evidence: tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
(docs-only ticket, no gate-affecting code changed; CLI-dispatch integration
test recorded per playbook section 5)

Filed: T-1683 (DEAD001/OPAQUE001 findings need a per-symbol symref
to avoid file-wide waiver amnesty)

Classification summary: surveyed every gate module owning a rule id in
_KNOWN_GATE_RULES (296 ids). Overwhelming majority already decide from a
resolved AST node, graph edge, or ticket-ledger model (class a). A small,
legitimately textual set (SEC001-004, EXCL001, frob fmt's directive wrap,
_rule_id_scan.py's own generator, TICK011's disclosure-phrase trigger,
WAIVE004's directive-parsing half) inspects raw text because its SUBJECT is
text -- no fix needed. Two class-(c) findings: REF001 (already this epic's
T-1665) and the new DEAD001/OPAQUE001 symref gap (T-1683). WALK001
was on the ticket's own evidenced-candidate shortlist but direct inspection
of _walk_lint.py shows it is AST-based and import-alias-aware for bare
calls -- reclassified (a), not (c); documented why in the doc's "Lexical
and wrong" section footnote so this is not re-derived from scratch.

Gates: frob check --ticket T-1663 --delta run below.

### Changed
```
 tickets.md | 43 +++++++++++++++++++++++++++++++++++++++++--
 1 file changed, 41 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 0 error(s), 3462 warning(s), 711 waived
- error-findings: none (measured, zero errors)
