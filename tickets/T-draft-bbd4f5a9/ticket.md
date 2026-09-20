---
id: T-draft-bbd4f5a9
title: N+1 git spawns and discarded caches on the doable, check, land, doctor and
  explore hot paths (perf audit 2026-09-20)
state: queued
kind: bug
origin: human
created: '2026-09-20'
priority: critical
parent: null
tier: story
sprint: v0.533.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_rapid_sweep.py
- src/frob/gates/__init__.py
- src/frob/tickets/_land.py
- src/frob/tickets/_unlanded.py
- src/frob/lang/__init__.py
- src/frob/app/explore_runner.py
- src/frob/app/ticket_runner/_close_cmd.py
- src/frob/app/ticket_runner/_lifecycle.py
scope_breadth_ack: true
scope_breadth_ack_reason: one audit, five independent hot-path fixes; split into child
  tickets at planning if leases collide
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
attachments:
- path: T-draft-bbd4f5a9/attachments/01-untitled.md
  caption: ''
  sha256: 61ae5aaf8e0c15d1db4babcbd841bf1b64899623cc7ece209cfe01ca0048ca45
acceptance:
- text: given the dev ledger, when frob ticket doable runs twice within the cache
    TTL, then the second run spawns no re-measure and completes in under 5 s
  evidence: []
- text: given the dev ledger, when frob check evaluates COV002, then the base-ledger
    read makes one git spawn
  evidence: []
- text: given the dev ledger, when frob doctor runs, then it completes in under 5
    s and spawns fewer than 50 subprocesses
  evidence: []
- text: given a warm artifact cache, when frob explore xref run_argv runs, then it
    completes in under 3 s with zero uncached parses
  evidence: []
- text: given a land precheck with 800 open tickets, when _find_leaked_tickets runs,
    then read_all_leases is called once
  evidence: []
threat: null
component: tickets
anchor: false
anchor_reason: null
land_commit: null
---
Measured 2026-09-20 on dev at 0.531.0, 691 open tickets, 11436 ledger commits. Full audit attached (perf-audit.md). Fix in this order. (H2) frob ticket doable 76s: _rapid_sweep._reproducing_identities_cached returns on the UNMEASURABLE branch (line ~3759) without calling _write_revalidation_cache (success path only, ~3768), so the 20s budget re-check (which always exceeds its budget+60s timeout at this size) is re-spawned on every call and buys nothing. Cache the negative outcome with a TTL and a known-unmeasurable sentinel that makes zero spawns; keep 'unmeasurable is never resolved'. Secondary: the child frob check --budget 20 runs past 80s, so --budget is not bounding; measure and fix separately if confirmed. (H3) frob check COV002: gates/__init__._ledger_states_at_base_v2 spawns git show <base>:<path> once per ticket file (~691 spawns per check on the land hot path); replace with one git cat-file --batch stream. (H4/H5) land precheck: _land._sibling_branch_ref re-runs read_all_leases per candidate, discarding the leases hoist T-4492 added one frame above; thread the hoisted leases through. _sibling_branch_touched_path spawns two git show per (sibling, path); batch. (M7) frob doctor 23s: _unlanded._directive_anchored_ticket_ids spawns git show per changed file per branch (719 spawns, 13 branches); one git grep -l frob:ticket <branch> -- <paths> or cat-file --batch per branch. (xref/map 11s) lang._parse_file_with_artifact_cache is a passthrough whenever PARSE_ARTIFACT_CACHE_ENV is unset, i.e. every single-process command; 1643 uncached parses per frob explore xref. Open the artifact cache read-only for explore commands. Also in the audit, lower priority: M1 git log -S per changed file in waive-audit, M2 cat-file -e per touched file in land baselines, M3 two spawns per commit in verify attribution, M4/M5 repeated load_queue in work --cluster and close (four loads), M6 BUG003 re-runs pytest per directive uncached.