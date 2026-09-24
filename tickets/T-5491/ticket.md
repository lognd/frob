---
id: T-5491
title: 'land CAS publish: ledger-only sibling commits are not absorbed by the T-4572
  fast path'
state: done
kind: bug
origin: human
created: '2026-09-24'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: v0.534.0
points: 5
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_land_squash.py
- tests/unit/test_land_cas_ledger_retry.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_land_squash.py
  reason: 'ledger-only CAS publish retry: distinguish apply-conflict-retryable from
    non-ledger-only refusal, scale attempt bound to observed drift'
  actor: logan
  at: '2026-09-24'
- op: add
  glob: tests/unit/test_land_cas_ledger_retry.py
  reason: 'ledger-only CAS publish retry: distinguish apply-conflict-retryable from
    non-ledger-only refusal, scale attempt bound to observed drift'
  actor: logan
  at: '2026-09-24'
triage_changes:
- field: points
  old_value: null
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-24'
evidence:
- tests/unit/test_land_cas_ledger_retry.py::TestLedgerOnlyAdvance::test_pure_ledger_advance_is_ledger_only
- tests/unit/test_land_cas_ledger_retry.py::TestLedgerOnlyAdvance::test_a_single_code_touching_commit_is_not_ledger_only
- tests/unit/test_land_cas_ledger_retry.py::TestRebaseComposedCommitOnto::test_rebased_commit_carries_the_same_content_change
- tests/unit/test_land_cas_ledger_retry.py::TestRebaseComposedCommitOnto::test_rebase_failure_returns_err
- tests/unit/test_land_cas_ledger_retry.py::TestFoldPublishAndResync::test_ledger_only_cas_miss_rebases_and_retries_without_regates
- tests/unit/test_land_cas_ledger_retry.py::TestFoldPublishAndResync::test_code_touching_cas_miss_falls_back_to_full_recompose
- tests/unit/test_land_cas_ledger_retry.py::TestFoldPublishAndResync::test_refused_land_leaves_root_clean
- tests/unit/test_land_cas_ledger_retry.py::TestFoldPublishAndResync::test_dev_advances_by_ledger_only_commit_between_compose_and_publish_lands
- tests/unit/test_land_cas_ledger_retry.py::TestAttemptLedgerOnlyRebase::test_ledger_only_apply_conflict_is_retryable_not_a_hard_refusal
- tests/unit/test_land_cas_ledger_retry.py::TestFoldPublishAndResync::test_apply_conflict_against_one_ledger_only_sibling_still_lands_after_a_second
designated_repro_test: tests/unit/test_land_cas_ledger_retry.py::TestFoldPublishAndResync::test_apply_conflict_against_one_ledger_only_sibling_still_lands_after_a_second
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-draft-a684db8f
branch: t-draft-a684db8f
---
Measured 2026-09-24: three lands (T-5324, T-5326, T-5474) were refused with "dev moved away while this land was composing" and each drift was ONE or TWO ledger-only sibling commits (chore(tickets): points T-5467; mirror scope T-5351; points T-5470), i.e. exactly the tickets/**-only advance T-4572's ledger-only CAS-retry fast path exists to absorb. Under a seven-agent fleet such commits arrive every few minutes, so the refusal now costs a full drain slot (10-25 minutes) several times per hour.

Fix: measure why the fast path did not absorb these (the log shows no ledger_only= line or attempt count near the refusal), make its attempt bound proportional to drift rate (or unbounded with backoff for pure-ledger advances), and log each attempt with the sibling commit list. Positive control: a test that advances dev with a tickets/**-only commit between compose and publish must land without a refusal.