---
id: T-3965
title: shellcheck stage over ops/**.sh
state: queued
kind: security
origin: agent
created: '2026-09-06'
priority: medium
parent: T-3942
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/check/_python.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given a shell script under ops/**.sh with a SC2097/SC2098-shaped issue, when
    frob check runs, then the new shellcheck stage reports it
  evidence: []
- text: given shellcheck is not installed in the environment, when frob check runs,
    then the stage degrades to a clear skip/warn rather than a hard crash
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
F-178 (T-3942 item 4). VERIFIED: git grep for shellcheck across src/frob found nothing -- frob has no shellcheck integration today. src/frob/check/_python.py and src/frob/check/_ts.py are the existing per-language stage runners (ruff/mypy for python, an analogous stage for ts) and are the right shape to mirror for a new _sh.py stage.

FINDING THIS WOULD HAVE CAUGHT: their D-M9 is SC2097/SC2098 (shellcheck's own codes for a misplaced env-var assignment before a command, silently not applying), a rule shellcheck already ships -- this is a matter of RUNNING an existing, mature external tool as a frob check stage, not writing new detection logic. Cheap.

Pairs with the ops shell-grammar-plus-starter-policy-catalogue ticket already filed on T-3928 (that one is about frob's OWN policy.pattern surface seeing ops/**.sh; this one is about running a battle-tested EXTERNAL linter over the same files as a stage, which is a much smaller lift and should not wait on the grammar/policy work). File and land independently.
