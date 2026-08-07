---
id: T-0986
title: promote DOC006 frob:tests target-form validation to ERROR (dotted-form mistakes
  recurred 4x)
state: done
kind: bug
origin: human
created: '2026-07-27'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_docptr.py
- frob.toml
- tests/test_docptr_gate.py
- src/frob/gates/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/__init__.py
  reason: 'DOC007 needs registering in src/frob/gates/__init__.py''s _KNOWN_GATE_RULES

    catalog (WAIVE002''s unwaivable-channel-rule computation and

    test_every_emitted_rule_literal_is_known both depend on every emitted rule

    id being present there) -- the new rule id cannot be introduced without this

    one-line catalog addition, discovered only once implementation started.

    '
  actor: logan
  at: '2026-07-27'
evidence:
- tests/test_docptr_gate.py::TestDoc006TestsTargetShape::test_double_separator_target_flagged
- tests/test_docptr_gate.py::TestDoc006TestsTargetShape::test_single_separator_target_not_flagged
- tests/test_gates.py::TestKnownGateRuleIds::test_every_emitted_rule_literal_is_known
designated_repro_test: null
acceptance:
- text: given a frob:tests directive whose target uses ::-separated class-method form,
    when frob check runs, then it fails at ERROR severity naming the directive, while
    dotted-form targets pass
  evidence:
  - tests/test_docptr_gate.py::TestDoc006TestsTargetShape::test_double_separator_target_flagged
  - tests/test_docptr_gate.py::TestDoc006TestsTargetShape::test_single_separator_target_not_flagged
  - tests/test_gates.py::TestKnownGateRuleIds::test_every_emitted_rule_literal_is_known
threat: null
component: null
---
Agents wrote pytest ::-separated class-method targets in frob:tests directives four separate times today (T-0715, T-0926, T-0976 x8, plus the runtime variant T-0983), each producing DRIFT002 errors on main post-land because the obligation graph keys dotted Class.method. T-0437 shipped DOC006 with frob:tests target-form hardening at WARN; promote exactly that recognized-shape check to ERROR (scoped severity or a dedicated rule id if the family cannot be split), so a mis-formed target refuses at the author gate instead of redding main after land. Verify the check catches the exact T-0976 shape (path::Class::method) and passes the dotted form.