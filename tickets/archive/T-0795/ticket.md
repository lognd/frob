---
id: T-0795
title: 'land: retry robustness -- close is not idempotent after own finalize (InvalidTransition
  done->done) + cwd-inside-worktree misdiagnosis'
state: done
kind: bug
origin: agent
created: '2026-07-23'
priority: critical
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_land.py
- src/frob/app/ticket_runner.py
- tests/test_ticket_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_ticket_land.py::TestLandRetryAfterFinalizeThenFail::test_retry_after_finalize_then_squash_failure_lands_the_diff
- tests/test_ticket_land.py::TestLandRetryAfterFinalizeThenFail::test_retry_when_still_queued_re_runs_the_ordinary_transition
- tests/test_ticket_land.py::TestLandRefusesWhenRootIsWorktree::test_refused_before_any_git_mutation_names_the_real_mistake
- tests/test_ticket_land.py::TestLandRefusesWhenRootIsWorktree::test_still_refuses_when_worktree_has_diverged_commits
designated_repro_test: null
acceptance:
- text: GIVEN a land that merged and finalized in the worktree but failed before committing
    to main WHEN land is retried with identical arguments THEN it completes the squash-apply
    onto main instead of erroring InvalidTransition on the already-done ticket; GIVEN
    land invoked with cwd inside the worktree THEN the error names the actual mistake
    (run from the root checkout) instead of the T-0640 false-green diagnosis
  evidence:
  - tests/test_ticket_land.py::TestLandRetryAfterFinalizeThenFail::test_retry_after_finalize_then_squash_failure_lands_the_diff
  - tests/test_ticket_land.py::TestLandRetryAfterFinalizeThenFail::test_retry_when_still_queued_re_runs_the_ordinary_transition
  - tests/test_ticket_land.py::TestLandRefusesWhenRootIsWorktree::test_refused_before_any_git_mutation_names_the_real_mistake
  - tests/test_ticket_land.py::TestLandRefusesWhenRootIsWorktree::test_still_refuses_when_worktree_has_diverged_commits
threat: null
component: null
---
Three lands this drive (T-0676, T-0774, T-0767) merged+finalized in the worktree (ticket transitioned to done in the worktree ledger) then failed before the main commit; every retry then errored InvalidTransition because close re-runs the done transition. Each required a manual splice-apply onto main (see the three land commits). Make the close step idempotent (done ticket + pending squash = proceed to squash-apply) or checkpoint the land so retry resumes at the squash. Separately, when root==worktree because the invoker's cwd is inside the worktree, say so explicitly.