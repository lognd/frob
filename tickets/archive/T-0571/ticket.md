---
id: T-0571
title: 'frob review: structured adversarial review channel as first-class evidence'
state: done
kind: feature
origin: agent
created: '2026-07-21'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/__main__.py
- src/frob/app/config.py
- src/frob/app/ticket_runner.py
- src/frob/tickets/__init__.py
- src/frob/tickets/_models.py
- tests/test_tickets_review.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/__main__.py
  reason: 'Porting T-0571 (frob review channel) salvage from stale worktree branch
    worktree-agent-a4f1c91fd4145fe43

    '
  actor: logan
  at: '2026-07-23'
- op: add
  glob: src/frob/app/config.py
  reason: 'Porting T-0571 (frob review channel) salvage from stale worktree branch
    worktree-agent-a4f1c91fd4145fe43

    '
  actor: logan
  at: '2026-07-23'
- op: add
  glob: src/frob/app/ticket_runner.py
  reason: 'Porting T-0571 (frob review channel) salvage from stale worktree branch
    worktree-agent-a4f1c91fd4145fe43

    '
  actor: logan
  at: '2026-07-23'
- op: add
  glob: src/frob/tickets/__init__.py
  reason: 'Porting T-0571 (frob review channel) salvage from stale worktree branch
    worktree-agent-a4f1c91fd4145fe43

    '
  actor: logan
  at: '2026-07-23'
- op: add
  glob: src/frob/tickets/_models.py
  reason: 'Porting T-0571 (frob review channel) salvage from stale worktree branch
    worktree-agent-a4f1c91fd4145fe43

    '
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/test_tickets_review.py
  reason: 'Porting T-0571 (frob review channel) salvage from stale worktree branch
    worktree-agent-a4f1c91fd4145fe43

    '
  actor: logan
  at: '2026-07-23'
evidence:
- tests/test_tickets_review.py::TestRecordReview::test_appends_approve_entry
- tests/test_tickets_review.py::TestRecordReview::test_blank_findings_rejected
- tests/test_tickets_review.py::TestRecordReview::test_multiple_reviews_append_only
- tests/test_tickets_review.py::TestRecordReview::test_unresolvable_commit_rejected
- tests/test_tickets_review.py::TestRecordReview::test_short_sha_normalized_to_full_sha
- tests/test_tickets_review.py::TestHasApprovedReviewForCommit::test_true_only_for_matching_approve
- tests/test_tickets_review.py::TestLoadRequireReviewForClose::test_defaults_false_with_no_frob_toml
- tests/test_tickets_review.py::TestLoadRequireReviewForClose::test_true_when_configured
- tests/test_tickets_review.py::TestLoadRequireReviewForClose::test_false_when_absent_from_section
- tests/test_tickets_review.py::TestReviewCli::test_cli_writes_review_record
- tests/test_tickets_review.py::TestReviewCli::test_cli_requires_all_flags
- tests/test_tickets_review.py::TestCloseStrictMode::test_strict_flag_alone_does_not_gate_without_config
- tests/test_tickets_review.py::TestCloseStrictMode::test_config_gate_alone_does_not_enforce_without_strict_flag
- tests/test_tickets_review.py::TestCloseStrictMode::test_both_gates_on_blocks_close_with_no_review
- tests/test_tickets_review.py::TestCloseStrictMode::test_both_gates_on_succeeds_with_matching_approve_review
- tests/test_tickets_review.py::TestCloseStrictMode::test_both_gates_on_succeeds_with_abbreviated_review_commit
- tests/test_tickets_review.py::TestCloseStrictMode::test_both_gates_on_blocks_close_with_stale_approve_review
designated_repro_test: null
threat: null
component: null
---
Adversarial review is this repo's most load-bearing quality mechanism (every false-confidence detector was caught by it) but lives only in dispatch prompts. frob review generate <diff|ticket> emits a per-diff checklist (detector changed -> demand counterexample; claim added -> demand refutation attempt; suppression code -> demand over-suppression probe); frob review record stores the verdict as a typed evidence channel consumable by close. Scope: new src/frob/review/, app runner, docs.