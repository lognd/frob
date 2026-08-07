---
id: T-0416
title: strata _sorted_py_files pruned walk now prunes nested git checkouts not covered
  by exclude globs (T-0414 caveat)
state: done
kind: bug
origin: human
created: '2026-07-20'
priority: medium
parent: T-0410
tier: ticket
sprint: null
scope:
- src/frob/strata/_code_binding.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_code_binding.py::TestBindCode::test_nested_git_checkout_pruned_even_when_not_covered_by_exclude_globs
designated_repro_test: null
threat: null
component: null
---
Reviewer non-blocking finding on T-0414: _sorted_py_files switched from rglob to a _should_prune_dir-pruned os.walk. _should_prune_dir prunes on is_skipped_dir + is_excluded + _is_nested_worktree, but the OLD rglob post-filter (_bind_all_files) only checked is_skipped_dir + is_excluded, NOT _is_nested_worktree. So the new walk additionally prunes nested git checkouts (dirs with a .git) even when they are NOT covered by [graph] exclude. In frobs own repo this is a no-op (exclude_globs covers .claude/worktrees/**), verified byte-identical. But for a downstream repo with a nested git checkout NOT in exclude globs, previously-bound .py files silently drop from strata bind_code -> could change SYS/selfconform findings. Decide: (a) accept as an intentional tightening (a nested git checkout is arguably never part of THIS repos source -- probably correct) and DOCUMENT it, or (b) make the walk match the old file set exactly by not pruning nested worktrees here. Either way the docstring must not assert "exact same final file set" unconditionally. Acceptance: behavior is documented/intentional, not silently asserted-equivalent; a test pins the chosen semantics for a repo with an uncovered nested checkout.