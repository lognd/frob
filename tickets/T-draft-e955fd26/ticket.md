---
id: T-draft-e955fd26
title: 'ticket land applies Tier-A fixes across the WHOLE tree and squashes them under
  the landing ticket: restrict to scope, add a disable list, gate TEST010'
state: queued
kind: bug
origin: agent
created: '2026-09-26'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: 0.534.0
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
- src/frob/app/ticket_runner/_land_cmd.py
- src/frob/gates/_fix_engine.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/app/config.py
  reason: config.py under live T-draft-fcfdafdf lease/in-progress state, collision
    blocks start; disabled-list config key deferred to a follow-up once that lease
    clears
  actor: logan
  at: '2026-09-26'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Reported by the logand.app-v2 session (2026-09-26, dev332/dev338):
`frob ticket land` runs `_tier_a_pre_land_step` -> `apply_tier_a_fixes`
before landing. Verified on dev b41443f46d: the step runs the WHOLE tree
(the T-1404 comment in _land_cmd.py says so; `touched_paths` only gates
the fmt half), `exclude` is a caller-only parameter (FMT001), there is no
CLI flag and no frob.toml knob to disable a fixer, and `--dry-run` skips
the step entirely (T-4179), so a clean dry run hides it.

Measured damage on logand main: T-0442's land (5f32ff6d, 67 files, 4 in
scope) shipped duplicated frob:tests lines with dangling `\` continuations
chaining into the next directive (the T-6535 TEST010 MOVE corruption)
into ~60 backend/tests/unit/*.py and tests/unit/*.py, committed as "wip:
pre-land snapshot for T-0442" and squashed under that ticket. T-0427's
land (dce72944, 46 files) did the same and was refused only because some
files were in T-0425's scope (CrossTicketLeakage); the commit was dropped.

Deliver:
1. At land, `apply_tier_a_fixes` receives the ticket's declared scope plus
   touched paths and rewrites nothing outside them; a fix that would touch
   an out-of-scope file is logged and skipped.
2. `[fix] disabled = ["TEST010", ...]` in frob.toml (and `--no-tier-a` on
   land as the explicit-flag tier) so a known-broken handler can be gated
   off in a consumer repo; TEST010's handler ships disabled by default
   until T-6535 lands and re-enables it.
3. A land whose pre-land Tier-A step rewrote a file outside scope refuses
   before the wip snapshot commit, naming the files (same posture as
   CrossTicketLeakage, no --allow flag).
4. Positive control: a fixture repo with a fixable TEST010 finding outside
   the ticket's scope; land leaves that file untouched and the land log
   names it as skipped.
Related: T-6535 (F-398 handler corruption), T-6543 (F-409 done-report
mutates the tree). Reproduction test: item 4.
