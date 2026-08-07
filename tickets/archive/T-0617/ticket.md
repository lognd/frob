---
id: T-0617
title: 'arch: OCP checks (ARCH1xx) -- type-dispatch smell, non-exhaustive enum match'
state: done
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
blocked_by:
- T-0609
parent: T-0330
tier: ticket
sprint: null
scope:
- src/frob/arch/_solid.py
- src/frob/arch/_models.py
- docs/modules/arch.md
- tests/unit/test_arch.py
- src/frob/arch/_ocp.py
- tests/unit/test_arch_ocp.py
- src/frob/arch/_patterns.py
- src/frob/arch/__init__.py
- pyproject.toml
- .frob-release.json
- uv.lock
- CHANGELOG.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/arch/_ocp.py
  reason: re-applying T-0617's already-implemented scope-adds after the 10b ledger
    restore reverted them (new _ocp.py module, isolated test file per concurrent T-0615/T-0616,
    _patterns.py shared-generator extraction, __init__.py registration, REL001 version-bump
    artifacts)
  actor: logan
  at: '2026-07-22'
- op: add
  glob: tests/unit/test_arch_ocp.py
  reason: re-applying T-0617's already-implemented scope-adds after the 10b ledger
    restore reverted them (new _ocp.py module, isolated test file per concurrent T-0615/T-0616,
    _patterns.py shared-generator extraction, __init__.py registration, REL001 version-bump
    artifacts)
  actor: logan
  at: '2026-07-22'
- op: add
  glob: src/frob/arch/_patterns.py
  reason: re-applying T-0617's already-implemented scope-adds after the 10b ledger
    restore reverted them (new _ocp.py module, isolated test file per concurrent T-0615/T-0616,
    _patterns.py shared-generator extraction, __init__.py registration, REL001 version-bump
    artifacts)
  actor: logan
  at: '2026-07-22'
- op: add
  glob: src/frob/arch/__init__.py
  reason: re-applying T-0617's already-implemented scope-adds after the 10b ledger
    restore reverted them (new _ocp.py module, isolated test file per concurrent T-0615/T-0616,
    _patterns.py shared-generator extraction, __init__.py registration, REL001 version-bump
    artifacts)
  actor: logan
  at: '2026-07-22'
- op: add
  glob: pyproject.toml
  reason: re-applying T-0617's already-implemented scope-adds after the 10b ledger
    restore reverted them (new _ocp.py module, isolated test file per concurrent T-0615/T-0616,
    _patterns.py shared-generator extraction, __init__.py registration, REL001 version-bump
    artifacts)
  actor: logan
  at: '2026-07-22'
- op: add
  glob: .frob-release.json
  reason: re-applying T-0617's already-implemented scope-adds after the 10b ledger
    restore reverted them (new _ocp.py module, isolated test file per concurrent T-0615/T-0616,
    _patterns.py shared-generator extraction, __init__.py registration, REL001 version-bump
    artifacts)
  actor: logan
  at: '2026-07-22'
- op: add
  glob: uv.lock
  reason: re-applying T-0617's already-implemented scope-adds after the 10b ledger
    restore reverted them (new _ocp.py module, isolated test file per concurrent T-0615/T-0616,
    _patterns.py shared-generator extraction, __init__.py registration, REL001 version-bump
    artifacts)
  actor: logan
  at: '2026-07-22'
- op: add
  glob: CHANGELOG.md
  reason: re-applying T-0617's already-implemented scope-adds after the 10b ledger
    restore reverted them (new _ocp.py module, isolated test file per concurrent T-0615/T-0616,
    _patterns.py shared-generator extraction, __init__.py registration, REL001 version-bump
    artifacts)
  actor: logan
  at: '2026-07-22'
evidence:
- tests/unit/test_arch_ocp.py::TestTypeDispatchSmell::test_isinstance_chain_flags_ocp_violation
- tests/unit/test_arch_ocp.py::TestTypeDispatchSmell::test_same_chain_also_still_recommends_strategy
- tests/unit/test_arch_ocp.py::TestTypeDispatchSmell::test_two_arm_isinstance_chain_not_flagged
- tests/unit/test_arch_ocp.py::TestNonExhaustiveEnumMatch::test_missing_member_flagged
- tests/unit/test_arch_ocp.py::TestNonExhaustiveEnumMatch::test_exhaustive_match_not_flagged
- tests/unit/test_arch_ocp.py::TestNonExhaustiveEnumMatch::test_wildcard_default_suppresses_finding
- tests/unit/test_arch_ocp.py::TestNonExhaustiveEnumMatch::test_capture_default_suppresses_finding
- tests/unit/test_arch_ocp.py::TestNonExhaustiveEnumMatch::test_non_enum_class_match_not_flagged
- tests/unit/test_arch_ocp.py::TestNonExhaustiveEnumMatch::test_union_pattern_covers_multiple_members
- tests/unit/test_arch_ocp.py::TestNonExhaustiveEnumMatch::test_unresolvable_pattern_shape_not_flagged
- tests/unit/test_arch.py::TestPatternRecommender::test_isinstance_chain_recommends_strategy
designated_repro_test: null
threat: null
component: null
---
type-dispatch smell: N+ isinstance/type==/tag-switch branches on one variable inside a function, flag as a polymorphism opportunity. non-exhaustive enum match: a match/switch over a known closed enum/tagged-union type missing a member and no wildcard/default. Static proxies, severity, ARCHxxx ids, T-0289-waivable. Acceptance: positive+negative fixtures per check; docs updated.