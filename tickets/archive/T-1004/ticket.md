---
id: T-1004
title: 'playbook + check --budget: eliminate the auto-background stall class'
state: done
kind: ux
origin: human
created: '2026-07-27'
priority: medium
parent: T-0999
tier: ticket
sprint: null
scope:
- docs/guides/agent-playbook.md
- src/frob/app/check_runner.py
- src/frob/check/**
- src/frob/__main__.py
- src/frob/app/config.py
- tests/unit/test_check_budget.py
- docs/commands/check.md
- docs/modules/app.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/__main__.py
  reason: CLI wiring (argparse + AppConfig field), new test file, check.md/app.md
    docs for the new --budget flag and AFFECT001 closure
  actor: logan
  at: '2026-07-27'
- op: add
  glob: src/frob/app/config.py
  reason: CLI wiring (argparse + AppConfig field), new test file, check.md/app.md
    docs for the new --budget flag and AFFECT001 closure
  actor: logan
  at: '2026-07-27'
- op: add
  glob: tests/unit/test_check_budget.py
  reason: CLI wiring (argparse + AppConfig field), new test file, check.md/app.md
    docs for the new --budget flag and AFFECT001 closure
  actor: logan
  at: '2026-07-27'
- op: add
  glob: docs/commands/check.md
  reason: CLI wiring (argparse + AppConfig field), new test file, check.md/app.md
    docs for the new --budget flag and AFFECT001 closure
  actor: logan
  at: '2026-07-27'
- op: add
  glob: docs/modules/app.md
  reason: CLI wiring (argparse + AppConfig field), new test file, check.md/app.md
    docs for the new --budget flag and AFFECT001 closure
  actor: logan
  at: '2026-07-27'
evidence:
- tests/unit/test_check_budget.py::TestSelectBudgetChunks::test_greedy_pack_fits_under_budget
- tests/unit/test_check_budget.py::TestSelectBudgetChunks::test_first_stage_always_selected_even_if_over_budget
- tests/unit/test_check_budget.py::TestSelectBudgetChunks::test_unmeasured_group_uses_default_estimate
- tests/unit/test_check_budget.py::TestSelectBudgetChunks::test_empty_remaining_selects_nothing
- tests/unit/test_check_budget.py::TestUpdateBudgetTiming::test_first_measurement_seeds_estimate_directly
- tests/unit/test_check_budget.py::TestUpdateBudgetTiming::test_later_measurement_blends_with_prior
- tests/unit/test_check_budget.py::TestUpdateBudgetTiming::test_does_not_mutate_input_dict
- tests/unit/test_check_budget.py::TestRunBudgetedCheck::test_runs_selected_chunks_and_reports_result
- tests/unit/test_check_budget.py::TestRunBudgetedCheck::test_persists_resume_state_for_deferred_groups
- tests/unit/test_check_budget.py::TestRunBudgetedCheck::test_resumes_from_prior_remaining_state
- tests/unit/test_check_budget.py::TestRunBudgetedCheck::test_clears_resume_state_once_every_group_has_run
- tests/unit/test_check_budget.py::TestRunBudgetedCheck::test_stale_remaining_group_is_dropped_and_falls_back_to_full_set
- tests/unit/test_check_budget.py::TestRunBudgetedCheck::test_budget_deferred_result_names_every_deferred_group
designated_repro_test: null
acceptance:
- text: given frob check --budget 120 on this repo, when it runs, then it completes
    under the budget having executed a coherent chunk subset and persists resume state
    for the remainder
  evidence:
  - tests/unit/test_check_budget.py::TestRunBudgetedCheck::test_persists_resume_state_for_deferred_groups
threat: null
component: null
---
Churn item 5 (~10 occurrences): agents run long commands, the harness auto-backgrounds at ~120s, and they wait for notifications that never come until nudged. Two-part fix: (a) rewrite the playbook sections that present backgrounding as normal -- foreground + explicit timeout wrappers is the only sanctioned pattern, with the T-0751 chunked recipes inline; (b) add frob check --budget <seconds>, which self-selects and orders stage chunks to fit the budget (reusing the T-0751 chunk state), removing the main reason agents run over.