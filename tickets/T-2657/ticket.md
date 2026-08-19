---
id: T-2657
title: Recovered from T-2615's phantom TICK006 citation of T-draft-5d1d5de0
state: dropped
kind: bug
origin: agent
created: '2026-08-19'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Auto-filed by the TICK006 Tier-A fix (T-1544): T-2615's Done report claimed T-draft-5d1d5de0 was filed, but T-draft-5d1d5de0 resolves to no block in tickets.md or tickets-archive.md -- a phantom filing trail. The original claim's own surrounding text (the only surviving description of the intended work) is quoted verbatim below; review and refine as needed.

> md` fragment or its CHANGELOG.md line --
those are data artifacts outside this ticket's declared scope
(`src/frob/release/_fragments.py` only). Filed T-draft-5d1d5de0 for
that cleanup now that the generator is fixed and won't recreate it.

Positive controls verified by test (all in `tests/test_relea

## Drop reason
- 2026-08-19: Draft T-draft-5d1d5de0's intended work (delete stray changelog.d/T-2593.md fragment, decide on the CHANGELOG.md T-2593 duplicated-id line) is already tracked and DONE under a separately-promoted real id: T-2641, same exact title 'clean up stray changelog.d/T-2593.md fragment left by the T-2615 bug', state=done. Measured: changelog.d/T-2593.md does not exist on current main (ls: No such file); CHANGELOG.md line 152 reads '- T-2641: clean up stray changelog.d/T-2593.md fragment left by the T-2615 bug', confirming T-2641 performed exactly this cleanup. The draft commit (9dff023e0, T-2615's worktree branch) never merged into main (git merge-base --is-ancestor 9dff023e0 main -> false) -- the TICK006 citation is phantom because the work was independently promoted/refiled as T-2641 through a different path, not lost. (absorbed by T-2641)
