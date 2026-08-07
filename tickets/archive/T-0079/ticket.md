---
id: T-0079
title: 'strata effect extraction: net/fs/exec facts vs may-capabilities'
state: done
kind: security
origin: human
created: '2026-07-17'
priority: medium
blocked_by:
- T-0052
parent: T-0053
tier: ticket
sprint: null
scope:
- src/frob/lang/**
- src/frob/strata/**
- tests/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_effects.py::TestExtractEffects::test_observes_net_fs_exec_effects_in_bound_code
- tests/unit/strata/test_effects.py::TestExtractEffects::test_foreign_files_are_not_scanned
- tests/unit/strata/test_effects.py::TestCheckCapabilityConformance::test_declared_may_capability_silences_matching_effect
- tests/unit/strata/test_effects.py::TestCheckCapabilityConformance::test_effect_with_no_matching_may_is_a_violation
- tests/unit/strata/test_effects.py::TestCheckCapabilityConformance::test_declared_may_of_different_kind_does_not_cover_effect
- tests/unit/strata/test_effects.py::TestCheckCapabilityConformance::test_foreign_code_is_not_checked
- tests/unit/strata/test_effects.py::TestCheckCapabilityConformance::test_fs_write_effect_needs_fs_kind_declaration
designated_repro_test: null
threat: tampering
component: null
---
Per-language extraction of socket/http/fs/subprocess surfaces; an effect with no may clause in its component fails; sound given std.policy.analyzable (tracked via enables).