## Done report

Implemented WIRE001/WIRE002 (src/frob/gates/_dead_symbols.py::wire_gate),
registered as the "wire" gate job in src/frob/gates/__init__.py
(_ALL_GATES, _PROCESS_POOL_GATES, _CANONICAL_GATE_ORDER) and the
gates-security stage group in src/frob/check/__init__.py, with
_KNOWN_GATE_RULES/_UNWAIVABLE_RULES entries in src/frob/gates/_waive.py
and CHK-GATE-WIRE001/CHK-GATE-WIRE002 in
docs/design/registry/check-coverage.yaml.

Scope was widened (frob ticket scope --add) to include
src/frob/gates/__init__.py, src/frob/gates/_waive.py,
src/frob/check/__init__.py, and docs/design/registry/check-coverage.yaml:
a gate function that is not registered in the job table, whose rule id
is not in _KNOWN_GATE_RULES, or whose registry entry is missing is
exactly the inert-code shape this ticket exists to catch, so landing
WIRE001 without also wiring it in would have made this ticket its own
eighth instance.

Three of the four case shapes named in the brief are implemented:
- a new function/method/class with no non-test caller (T-1421's shape) --
  a best-effort repo-wide text scan (_is_reached_outside_diff_tests),
  deliberately NOT frob.graph.callgraph's build_call_graph/
  build_reference_graph substrate: both resolve an edge only when the
  CALLEE is private, which is backwards for WIRE001 (its motivating
  instances, own_obligations_clean/bug_repro_violations, are both
  public, exactly what DEAD001 exempts).
- a new gate rule id absent from _KNOWN_GATE_RULES (T-1421's BUG002
  shape) -- a rule=<literal> check against known_gate_rule_ids().
- a new CLI flag dest absent from _config_external.py's copy lists
  (T-1422's shape, the one called out as hardest/invisible to any call
  graph) -- a targeted string-membership check over that file's current
  text, not a generalization of the call-graph machinery.

Not implemented: a new keyword-only parameter no call site passes
(T-1384/T-1399/T-1391's shape) -- needs a signature-level before/after
diff neither of the two mechanisms above covers (the enclosing function
already has callers, so the no-caller check does not fire; the new
PARAMETER being unpassed is a narrower question). Disclosed and filed as
a follow-up (see Filed below).

The escape hatch is an enforced obligation, not free-text prose: WIRE002
(error, unwaivable) fires when a frob:waive WIRE001 lacks a
follow_up="T-####" attribute naming a real, still-open ticket, or names
one that is closed/nonexistent.

Waive directives that disappeared from this diff, per land's
OutOfScopeWaiveDeletion guard: none removed. Two waivers were only
REFLOWED (identical reason text, different line-wrap points) by land's
own pre-land Tier-A auto-fix pass (frob fmt directive canonicalization),
outside this ticket's original scope but harmless and scoped in:
- src/frob/tickets/_accept.py : INV006 (line-wrap reflow only, same reason
  text, T-1427's original waiver)
- tests/unit/test_ticket_close_bug002_t1427.py : OPAQUE001 (line-wrap
  reflow only, same reason text, T-1427's original waiver)

Self-demonstration, measured via `frob check --ticket T-1428 --delta`
against a freshly stamped baseline covering all 40 gate families:
BEFORE this ticket's diff, the "wire" gate group did not exist at all
(0 gate families named "wire" in _ALL_GATES on main). AFTER, with WIRE001/
WIRE002 registered and this ticket's own diff checked against itself, the
wire group reports 0/5 new violations -- WIRE001 finds zero problems with
the diff that adds it, confirming both regression directions:
- WIRE001 REFUSES an unreachable addition: TestWireGate.
  test_new_public_function_with_no_caller_is_flagged reconstructs T-1421's
  shape (a guard function, unit-tested directly, no non-test caller) and
  the gate fires WIRE001 on it. Same shape verified for the rule-id
  (BUG002-style) and CLI-dest (T-1422-style) cases via
  test_new_rule_id_missing_from_known_gate_rules_is_flagged and
  test_new_cli_dest_missing_from_config_external_is_flagged.
- A properly wired change is PERMITTED: test_new_function_called_from_non_
  test_code_is_not_flagged, test_new_rule_id_present_in_known_gate_rules_
  is_not_flagged, and test_new_cli_dest_present_in_config_external_is_not_
  flagged all show the clean case passes; the wire_gate function itself,
  registered into __init__.py/_waive.py/check-coverage.yaml in the same
  diff that adds it, is likewise not flagged by its own rule (the 0/5 new
  figure above).

Docs: docs/modules/gates.md rule-catalog table rows plus a
"WIRE001/WIRE002 (T-1428)" detail section (mirrors the existing
DEAD001/SUPPRESS001 sections' shape).

Filed: T-1430 (kwonly-parameter-added shape, follow-up to the
disclosed cut above -- verify the real renumbered id on main before citing
further).

Gates: frob check --ticket T-1428 --delta clean (0 new across every gate
family run, including wire=0/5 new); ruff check/format, ty check all
clean on every touched file.

### Changed
```
 design/frob.strata                           |   2 +
 docs/design/registry/check-coverage.yaml     |  18 +-
 docs/modules/gates.md                        |  74 ++++++
 src/frob/check/__init__.py                   |   1 +
 src/frob/gates/__init__.py                   |  12 +-
 src/frob/gates/_dead_symbols.py              | 348 +++++++++++++++++++++++++++
 src/frob/gates/_waive.py                     |  15 ++
 src/frob/tickets/_accept.py                  |  12 +-
 tests/test_gates.py                          | 230 ++++++++++++++++++
 tests/unit/test_ticket_close_bug002_t1427.py |  12 +-
 tickets.md                                   | 224 ++++++++++++++++-
 11 files changed, 929 insertions(+), 19 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestWireGate::test_new_public_function_with_no_caller_is_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestWireGate::test_new_function_called_from_non_test_code_is_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestWireGate::test_new_rule_id_missing_from_known_gate_rules_is_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestWireGate::test_new_rule_id_present_in_known_gate_rules_is_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestWireGate::test_new_cli_dest_missing_from_config_external_is_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestWireGate::test_new_cli_dest_present_in_config_external_is_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestWireGate::test_wire002_fires_when_follow_up_ticket_missing` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestWireGate::test_wire002_fires_when_follow_up_ticket_is_closed` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestWireGate::test_wire002_clean_when_follow_up_ticket_is_open` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 9 passed (from 9 evidence id(s))
- gates: 5 error(s), 1104 warning(s), 696 waived
- error-findings: PERF003@src/frob/gates/_dead_symbols.py, REG005@docs/design/registry/check-coverage.yaml, REG007@docs/design/registry/check-coverage.yaml, WIRE001@src/frob/gates/_dead_symbols.py, WIRE001@tests/test_gates.py
