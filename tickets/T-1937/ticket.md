---
id: T-1937
title: 'Gate rule registry is not authoritative: 10 live rule ids bypass the acceptance
  preflight'
state: done
kind: bug
origin: human
created: '2026-08-09'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_rule_id_scan.py
- src/frob/gates/__init__.py
- src/frob/gates/_waive.py
- tests/gates/test_rule_id_scan_branches.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/__init__.py
  reason: add the 8 registry gaps + broaden the completeness-scan drift-lock test,
    T-1937 (tests/test_gates.py held by T-1881's live lease, worked around)
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/gates/_waive.py
  reason: add the 8 registry gaps + broaden the completeness-scan drift-lock test,
    T-1937 (tests/test_gates.py held by T-1881's live lease, worked around)
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/gates/test_rule_id_scan_branches.py
  reason: add the 8 registry gaps + broaden the completeness-scan drift-lock test,
    T-1937 (tests/test_gates.py held by T-1881's live lease, worked around)
  actor: logan
  at: '2026-08-10'
evidence:
- tests/gates/test_rule_id_scan_branches.py::TestScanCandidateRuleIdLiterals::test_finds_bare_positional_argument
- tests/gates/test_rule_id_scan_branches.py::TestScanCandidateRuleIdLiterals::test_finds_typed_const_assignment
- tests/gates/test_rule_id_scan_branches.py::TestScanCandidateRuleIdLiterals::test_finds_code_kwarg_outside_scanned_bases
- tests/gates/test_rule_id_scan_branches.py::TestScanCandidateRuleIdLiterals::test_inline_comment_example_not_picked_up
- tests/gates/test_rule_id_scan_branches.py::TestScanCandidateRuleIdLiterals::test_whole_line_comment_not_picked_up
- tests/gates/test_rule_id_scan_branches.py::TestFindUnregisteredRuleIds::test_empty_when_every_candidate_is_known_or_retired
- tests/gates/test_rule_id_scan_branches.py::TestFindUnregisteredRuleIds::test_reports_a_candidate_missing_from_both_known_and_retired
- tests/gates/test_rule_id_scan_branches.py::TestFindUnregisteredRuleIds::test_retired_id_is_excluded_even_when_shape_matches
- tests/gates/test_rule_id_scan_branches.py::TestFindUnregisteredRuleIds::test_real_repo_registry_is_complete
- tests/test_gates.py::TestKnownGateRuleIds::test_every_emitted_rule_literal_is_known
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
AUDIT FINDING (full gate audit, 2026-08-09).

`_KNOWN_GATE_RULES` is documented as the AUTHORITY for which rule ids are
live, and `frob.tickets._new_gate_rule_acceptance` scrapes that literal's
SOURCE TEXT to detect newly-added rule ids for the T-0756 close/land
acceptance-policy preflight.

MEASURED: 288 quoted rule-id literals exist under src/; 9 are live but
absent from the registry -- BUDGET001, CHECK001, CVEFP001, DEPLOY001,
DEPLOY002, DEPLOY003, DERIVED001, SYS109, TIERBDEMO001. SYS104 is also
absent despite 390 ledger references and being mandatory since T-1113.

IMPACT: a soundness hole in a META-GATE. A rule added outside
SCANNED_BASES -- or in a construction shape the scan misses -- is
invisible to the acceptance preflight, so it ships WITHOUT the
acceptance-policy review that preflight exists to force. Two of the nine
(SYS109, TIERBDEMO001) live INSIDE src/frob/gates/ and were still missed,
so this is not only the disclosed out-of-base gap: shape detection leaks
within its own declared territory too.

The gap IS disclosed in `_rule_id_scan.py`'s docstring, but disclosure is
not enforcement -- it has since grown to 10 rules and nothing measures it.
Prefer making registry completeness self-checking across all of src/
(automatic) over documenting the caveat harder.