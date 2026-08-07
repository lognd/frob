---
id: T-1202
title: 'refactor: alias-conflict policy'
state: done
kind: feature
origin: human
created: '2026-07-29'
priority: medium
blocked_by:
- T-1197
parent: T-1197
tier: ticket
sprint: null
scope:
- src/frob/refactor/**
- docs/commands/refactor.md
- tests/test_refactor.py
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: design/frob.strata
  reason: sync-interface must write the new refactor/testsuite interface attrs for
    this ticket's new public symbols
  actor: logan
  at: '2026-08-03'
evidence:
- tests/test_refactor.py::TestAliasPolicy::test_build_plan_error_policy_still_refuses
- tests/test_refactor.py::TestAliasPolicy::test_rename_dest_renames_existing_symbol_and_its_callers
- tests/test_refactor.py::TestAliasPolicy::test_build_plan_rename_dest_policy_proceeds
- tests/test_refactor.py::TestScanReferences::test_auto_alias_on_call_site_name_collision
designated_repro_test: null
acceptance:
- text: 'GIVEN an import-site name collision during a move/rename with no

    --alias-conflict flag given WHEN the plan phase detects it THEN an

    alias is auto-generated at the import site only and named in the

    disclosed alias report'
  evidence:
  - tests/test_refactor.py::TestScanReferences::test_auto_alias_on_call_site_name_collision
- text: 'GIVEN a destination-namespace collision (two same-named symbols would

    land in the same module) WHEN the plan phase detects it THEN it refuses

    under the default `error` policy, and only proceeds if `--alias-conflict

    rename-dest` was explicitly passed'
  evidence:
  - tests/test_refactor.py::TestAliasPolicy::test_build_plan_error_policy_still_refuses
  - tests/test_refactor.py::TestAliasPolicy::test_rename_dest_renames_existing_symbol_and_its_callers
  - tests/test_refactor.py::TestAliasPolicy::test_build_plan_rename_dest_policy_proceeds
- text: 'GIVEN a completed refactor with at least one auto-generated alias WHEN

    its report is printed THEN every alias appears in a distinct, clearly

    labeled section of the report, never buried in the general rewrite list'
  evidence:
  - tests/test_refactor.py::TestAliasPolicy::test_rename_dest_renames_existing_symbol_and_its_callers
  - tests/test_refactor.py::TestAliasPolicy::test_build_plan_rename_dest_policy_proceeds
threat: null
component: null
---
Design: docs/design/refactor-verb.md (T-1135). T-1197's plan/apply
pipeline needs an extension point for handling an import-site name
collision when a destination name is already bound; this ticket owns
that policy layer: the naming scheme for auto-generated aliases, the
`--alias-conflict {error,rename-dest}` flag (default: error -- a
destination-namespace collision is a hard refusal, never a silent
auto-rename of the destination module's own symbol), and the disclosed
alias report format (every auto-generated import alias named, so a human
reviews it rather than discovering it later in a diff).

Depends on T-1197 exposing the plan-phase hook this policy plugs into
(a callback invoked once per detected collision, returning either an
alias name or a refusal).