---
id: T-2458
title: scan_candidate_rule_id_literals false positive on docstring prose (COV0011
  example)
state: done
kind: bug
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_gates_schema.py
evidence_scope:
- tests/gates/test_rule_id_scan_branches.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/gates/test_rule_id_scan_branches.py::TestFindUnregisteredRuleIds::test_real_repo_registry_is_complete
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 7adf323038bf711bcc0efde351dd19db59c3a6e8
---
T-2448's own standing-gate work surfaced a pre-existing false positive
in scan_candidate_rule_id_literals (frob.gates._rule_id_scan): the
existing repo-wide completeness test
(tests/gates/test_rule_id_scan_branches.py::TestFindUnregisteredRuleIds::test_real_repo_registry_is_complete)
now fails on main with:

  {'COV0011': 'src/frob/gates/_gates_schema.py:22'}

"COV0011" is not a real gate rule id -- it is a deliberate misspelling
used as a PROSE EXAMPLE inside src/frob/gates/_gates_schema.py's module
docstring (illustrating exactly the kind of misspelled-key bug that
gate's own logic exists to catch). scan_candidate_rule_id_literals
skips lines starting with "#" but this text sits inside a triple-quoted
module docstring, not a # comment, so the exclusion never fires.

This is a real, pre-existing gap (confirmed failing on a completely
clean checkout of main, unrelated to any T-2448 change) -- filed
separately rather than fixed inline since it requires either widening
scan_candidate_rule_id_literals's comment/docstring-prose exclusion
(same self-match problem _rule_id_scan.py already solved for its OWN
module) or rewording the docstring to avoid a quoted rule-id-shaped
literal. Whoever picks this up: prefer the docstring reword if it's a
one-off (least code-risk), the scanner fix if this pattern (a real
example inside a gate module's own docstring) recurs.