## Done report

Premise held: both named tests still fail on main. Reproduced directly:
tests/test_check_coverage_registry.py's unfiltered scan found 4 findings
on check-coverage.yaml (1 REG005 denominator drift + 3 REG002 dangling
handled_by references for TDD001/VMOD001/VERSION001, not "4 REG005" as
the ticket's own description summarized -- the ticket conflated all four
under one label). test_no_reg008_findings_for_check_coverage_yaml found
6 REG008 findings, not the 4 the ticket described: 2 of those 6
(CPLACE001, CPLACE002) are a REGRESSION FROM MY OWN T-3218 land earlier
tonight -- landing that gate auto-added handled_by:CPLACE001/CPLACE002
entries to check-coverage.yaml via a Tier-A registry fix, with no
matching frob:enforces CHK-GATE-CPLACE001/002 in code yet. The other 4
(NARR001, TDD001, VMOD001, F401) were pre-existing.

Fix applied:
- REG005: docs/design/registry/check-coverage.yaml gate_rule_total
  350 -> 351 (matches the actual entry count).
- REG008 (all 6): added `# frob:enforces CHK-GATE-<RULE>` directly above
  each rule's own enforcing function --
  scan_cplace001_waive_reason_length/scan_cplace002_docs_narrative
  (src/frob/gates/_comment_placement.py, my own T-3218 regression),
  narrative_blocks_gate (src/frob/gates/_narrative_blocks.py),
  tdd_order_violations (src/frob/gates/_tdd_order.py), vmodel_gate
  (src/frob/gates/_vmodel.py), and _is_ruff_error_code
  (src/frob/process/parsers/ruff.py, same site I001 already carries its
  own CHK-GATE-I001 directive).
  tests/test_registry_exhaustiveness.py::TestCheckCoverageReg008BurnDown::test_no_reg008_findings_for_check_coverage_yaml
  is now fully green.

NOT FIXED, explicit cut: REG002's 3 dangling handled_by references
(TDD001, VMOD001, VERSION001) need registering in
src/frob/gates/_waive.py::_KNOWN_GATE_RULES -- the same one-line-per-id
pattern T-3218 used for CPLACE001/CPLACE002. Attempted this; refused with
ScopeLeaseConflict: T-2931 holds a live in-progress lease on
src/frob/gates/_waive.py for an unrelated WIRE001 change (confirmed via
`frob ticket show T-2931`, state=in-progress). Per the standing recovery
recipe for a real lease conflict, did not force it. Reverted the
_waive.py edit and filed T-3239 (promoted from T-3239) to carry
that specific fix once T-2931's lease clears.
tests/test_check_coverage_registry.py::TestExhaustivenessGateOverRealCheckCoverage::test_no_check_coverage_violations
therefore still fails on this land, now with exactly 3 REG002 findings
(down from 4 mixed findings) -- T-3239 closes the remaining gap.

Evidence:
tests/test_registry_exhaustiveness.py::TestCheckCoverageReg008BurnDown::test_no_reg008_findings_for_check_coverage_yaml
tests/gates/test_comment_placement.py (regression check, all 12 green)
tests/test_narrative_blocks.py (regression check, all green)
tests/gates/test_tdd_order.py (regression check, all green)
tests/test_gates_vmodel.py (regression check, all green)

Filed: T-3239 (promoted from T-3239) -- register
TDD001/VMOD001/VERSION001 in _KNOWN_GATE_RULES, blocked on T-2931's
_waive.py lease.
