---
id: T-5178
title: pre-land DOC004/DOC006 sweeps resolve console commands and options against
  the running parser, not the staged tree
state: queued
kind: bug
origin: human
created: '2026-09-21'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_docptr.py
- tests/unit/gates/test_docptr.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: recording a third measured occurrence of T-5178's own bug, found while landing
    T-4695
  actor: logan
  at: '2026-09-22'
  old_length: 1117
  new_length: 1657
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED 2026-09-21 on two lands: T-4437 (docs/modules/clean.md documents --sweep-disposable-worktrees, added to frob clean by the same land) was refused with DOC006 'not a known option of frob clean'; T-4578 (docs/commands/scaffold.md documents 'frob scaffold unity-project', a subcommand the same land adds) was refused with DOC004 'does not resolve to a known subcommand'. Both docs are correct for the tree being landed. frob.gates._docptr builds console_parsers/console_trees by importing the parser of the frob that is RUNNING (the root checkout's dev code), so any land that adds a CLI leaf or option and documents it in the same change is refused by its own pre-land sweep; the only exits were inline frob:waive DOC004/DOC006 comments (both now on dev). Fix: resolve pointers against the staged merge preview (import the parser module from the staged tree in a subprocess, or diff the staged _cli_parsers/* for added leaves/options and treat those as known), and add a regression test: a staged change that adds a subcommand plus a doc mentioning it must pass DOC004/DOC006. Remove the two waivers once fixed.

MEASURED 2026-09-22 on a third land: T-4695 (docs/commands/gitlog.md documents 'frob explore gitlog', a subcommand the same land adds) was refused with DOC006 'does not resolve to a known subcommand' -- same root cause as the T-4437/T-4578 instances above (frob.gates._docptr resolves against the RUNNING parser, not the staged tree). Exit was the same inline frob:waive DOC006 workaround, now on dev. This is the third confirmed instance of the same bug; the fix (stage-tree parser resolution) should also remove this waiver once landed.