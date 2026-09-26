---
id: T-6579
title: frob ticket new hung for 5 h in D state at 1.7 GB RSS in the crunk repo (global
  tool, duplicate title)
state: queued
kind: bug
origin: agent
created: '2026-09-26'
priority: high
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
- src/frob/app/ticket_runner/_new.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'crunk root cause: 9P PATH walk during ticket mutations'
  actor: logan
  at: '2026-09-26'
  old_length: 996
  new_length: 2416
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Measured 2026-09-26 10:25 UTC: pid 708425, `frob ticket new --title "Screen
discovery adapter: React Router routes.tsx scanner" --kind feature --parent
T-0158 --scope src/cr...` from the global uv tool (dev 5e69b3fb68), cwd
/home/logan/projects/crunk, 19271 s elapsed, 2190 s CPU, state D, RSS
1.7 GB, wchan 0. A ticket with that exact title already existed (T-0174);
the duplicate-title path should refuse in under a second. The crunk root was
clean and no new ticket dir appeared; the owner killed it.

Investigate what a `ticket new` does that can grow to 1.7 GB and run for
hours (the --ack-related graph walk? a full check? a lock spin on
.frob/tickets.lock?) and bound it: a wall-clock deadline on every
subprocess or lock wait inside `ticket new` with a refusal naming the
stage, and the duplicate-title check before any graph or check work.
Positive control: a test that plants a held tickets.lock and shows ticket
new refuses with the lock holder within the deadline instead of waiting.


Root cause (crunk-ba, 2026-09-26, four more instances): `frob ticket body
--append`, `done-report`, `scope --add` and a logand `ticket body` had sat
in D state for 1-3 h with /proc/<pid>/wchan = p9_client_rpc, WSL's 9P
client: every one of them was inside a Windows-side (/mnt/c) path probe.
This is the F-023 class already documented at
src/frob/app/ticket_runner/_new.py (the clipboard probe's powershell.exe
exec hung in the PATH-search stat() calls before subprocess's timeout
clock starts), but the T-3322 opt-in gate only covers the clipboard
offer in `ticket new`; body/scope/done-report never reach that gate and
still hang, so the exec that hangs is a different spawn on the mutation
path (any bare-name `subprocess.run` of git/ruff/pytest walks the 43
appended /mnt/c PATH entries when the 9P mount stalls).

Deliver: (1) a single process-wide spawn PATH that strips /mnt/* entries
(honouring WSL's appendWindowsPath=false semantics) used by every
`gitio`/tool spawn, with the resolved absolute path cached per binary;
(2) a wall-clock deadline around the spawn itself (fork/exec), not only
the wait, on every ticket-mutation subprocess, refusing with the stage
name; (3) `frob doctor` reports appended Windows PATH entries on WSL as
a hang risk. Positive control: a fake PATH entry on a FUSE mount that
blocks stat() plus a `ticket body --append`; the verb completes within
the deadline instead of hanging.
