---
id: T-1590
title: 'suite red: extending-guides drift, exports residue, unregistered gate rule
  literal'
state: done
kind: bug
origin: human
created: '2026-08-05'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- docs/guides/**
- src/frob/gates/_secrets.py
- src/frob/**/__init__.py
- src/frob/gates/**
- tests/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_extending_guides_complete.py::TestExtendingGuidesComplete::test_every_row_anchor_file_exists_and_mentions_guide
- tests/unit/test_extending_guides_complete.py::TestExtendingGuidesComplete::test_every_anchor_fragment_resolves_to_guide_h1
- tests/unit/test_extending_guides_complete.py::TestExtendingGuidesComplete::test_every_probe_still_matches_source
- tests/unit/test_extending_guides_complete.py::TestExtendingGuidesComplete::test_probe_table_and_inventory_agree
- tests/unit/test_exports.py::TestFrobExportsPolicyResidue::test_all_nine_packages_report_zero_missing_symbols
- tests/test_gates.py::TestKnownGateRuleIds::test_every_emitted_rule_literal_is_known
designated_repro_test: null
threat: null
component: null
---
Three real (isolation-reproducible) suite failures on main:

1. tests/unit/test_extending_guides_complete.py x3 -- docs/guides/extending-* drift against src/frob/gates/_secrets.py: the probe 'class _SecretPattern' for row 'secrets-scan-providers' no longer matches source, the row's anchor fragment does not resolve to a guide h1, and _secrets.py has no frob:doc anchor pointing back at the guide. Someone renamed/moved the secrets-scan provider shape without updating the guide's row+anchor pair.

2. tests/unit/test_exports.py::TestFrobExportsPolicyResidue -- frob-exports reports missing symbols for src/frob (and possibly other packages); public symbols added during this drive were never added to their package __init__.

3. tests/test_gates.py::TestKnownGateRuleIds::test_every_emitted_rule_literal_is_known -- a rule id literal is constructed in src/frob/gates or src/frob/strata that is not in the known-rule registry. Every emitted rule must be registered (that registry is what WAIVE002/docs generation read).

All three are 'the code moved, the declarations did not' -- fix the declarations, do not relax the tests.