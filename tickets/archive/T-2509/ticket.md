---
id: T-2509
title: frob ticket evidence --check-repro ignores explicit --base-ref, always resolves
  to a fixed unrelated commit
state: done
kind: bug
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_evidence.py
- src/frob/app/ticket_runner/_verify.py
- src/frob/gitio.py
evidence_scope:
- tests/unit/test_ticket_runner_repro_merge_base.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/app/ticket_runner/_verify.py
  reason: 'T-2509: root cause is _merge_base(root, base_ref) computing merge-base
    against the PRIMARY checkout''s own HEAD (via _evidence_check_repro in _verify.py),
    not the ticket worktree''s actual HEAD -- not in _evidence.py at all, the ticket''s
    original file guess was wrong'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/gitio.py
  reason: 'T-2509: root cause is _merge_base(root, base_ref) computing merge-base
    against the PRIMARY checkout''s own HEAD (via _evidence_check_repro in _verify.py),
    not the ticket worktree''s actual HEAD -- not in _evidence.py at all, the ticket''s
    original file guess was wrong'
  actor: logan
  at: '2026-08-18'
evidence:
- tests/unit/test_ticket_runner_repro_merge_base.py::TestReproMergeBaseRoot::test_prefers_frob_worktree_env_when_set
- tests/unit/test_ticket_runner_repro_merge_base.py::TestReproMergeBaseRoot::test_falls_back_to_root_when_unset
- tests/unit/test_ticket_runner_repro_merge_base.py::TestExplicitBaseRefHonoured::test_explicit_base_ref_on_own_branch_is_honoured_not_collapsed_to_fork_point
- tests/unit/test_ticket_runner_repro_merge_base.py::TestExplicitBaseRefHonoured::test_distinct_ancestors_resolve_distinctly
- tests/unit/test_ticket_runner_repro_merge_base.py::TestExplicitBaseRefHonoured::test_root_without_fix_reproduces_the_original_bug
- tests/unit/test_ticket_runner_repro_merge_base.py::TestWarnIfBaseRefNotHonouredExactly::test_no_warning_when_base_ref_already_matches
- tests/unit/test_ticket_runner_repro_merge_base.py::TestWarnIfBaseRefNotHonouredExactly::test_warns_when_base_ref_is_not_an_ancestor
designated_repro_test: tests/unit/test_ticket_runner_repro_merge_base.py::TestExplicitBaseRefHonoured::test_explicit_base_ref_on_own_branch_is_honoured_not_collapsed_to_fork_point
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 8335911c239c32b3ce3a961c43ddb4569d129b75
---
Found while working T-2498. `frob ticket evidence T-#### --check-repro
NODE-ID --base-ref SHA` did not use the passed SHA consistently: with no
--base-ref it correctly resolved 'main' and refused SAME_AS_HEAD when
main==HEAD; but every explicit --base-ref sha I passed (several different,
valid, reachable commits in the ticket's own worktree branch) all resolved
to the SAME fixed commit as the checked "parent" tree, regardless of which
sha was given. This made the T-2021 "commit the repro test alone, pass its
sha as --base-ref" recipe (documented in the tool's own error message and
docs/modules/tickets.md#check-repro-post-land-limitation-t-2025)
unworkable for T-2498's evidence -- verification had to fall back to a
manual scratch-worktree pytest run instead of the sanctioned CLI path.

Reproduction: worked in .claude/worktrees/t-2498 (branch t-2498). Commits
in order: A (test only, no fix) -> B (fix, child of A). Ran
`frob ticket evidence T-2498 --check-repro NODE-ID --base-ref A` and
`--base-ref B` (B's own hash) -- both invocations reported checking the
SAME tree, `e86d42d13...` ("chore(rapid): record T-2479's deferred
post-land sweep"), which is neither A nor A^ nor B nor B^ in any
consistent pattern across the two calls (matched A^ in one earlier
attempt with a different sha, then diverged). Investigate whether
--base-ref resolution silently falls back to the ticket's OWN recorded
parent_commit field instead of the CLI value, or some other stale-cache/
resolution bug.

Suggest: add a targeted regression test that asserts --check-repro's
resolved comparison commit is a deterministic, correct function of the
literal --base-ref value passed (not a ticket metadata field, not a
cached prior resolution), across at least 2 distinct sha inputs in one
test run.