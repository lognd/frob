---
id: T-draft-36c10996
title: Diff-driven gates (AFFECT/FMT/COV002/pre-commit land-owned-file guard) compare
  against stale local 'main' instead of 'dev', flooding worktree checks/commits with
  unrelated noise
state: queued
kind: bug
origin: human
created: '2026-09-27'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
flavour: null
due: null
rank: null
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: null
branch: null
scope:
- src/frob/scaffold/project.py
- src/frob/gates/__init__.py
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
found while working T-5633: gate:AFFECT/gate:FMT/gate:COV (COV002/TODO001) and the T-0731 pre-commit land-owned-files guard all hardcode a comparison against the local 'main' ref to find 'what changed in this diff'. In this repo 'main' is hundreds of commits behind the real integration branch 'dev' (b10d67a0f2 vs 86603289ec), so ANY worktree branched from dev sees thousands of unrelated pre-existing files reported as part of 'its own diff' (e.g. AFFECT001 on strata-core/src/parse/grammar_policy.rs, FMT001 on strata-core/src/graph/vmodel/closure.rs, from a T-5633 check that touched neither) -- and a plain 'git merge dev' that legitimately carries dev's own already-landed CHANGELOG.md/uv.lock/pyproject.toml content trips the T-0731 guard's _t1742_staged_diverges_from_main check outright, since that content necessarily differs from stale main. Needs either a config knob for the comparison ref or teaching these checks to use the ticket's actual base branch.