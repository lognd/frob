---
id: T-3217
title: 'UNCONFIRMED-ONCE: close-guard false-fire + sqlite ''database is locked'' crash
  under concurrent frob check load'
state: in-progress
kind: bug
origin: human
created: '2026-08-28'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_close_cmd.py
- src/frob/tickets/_reporting.py
- src/frob/cache
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
UNCONFIRMED-ONCE observation, migrated from the now-removed tracked
scratch file `.claude-scratch/T-3122-close-guard-repro-capture.md`
(T-3181 cleanup of tracked agent-scratch paths). Captured 2026-08-27
during series BT (T-3122 implementation), under a concurrent
`frob ticket land T-3115` and 6 concurrent fleet `frob check` runs.

Applying the same standard T-3131 set: this was already NOT reproduced
(direct calls to the exact guard functions returned clean, subsequent
CLI attempts timed out rather than re-showing the error or succeeding).
Filed as a one-sighting observation with its load conditions recorded,
not as open investigative work -- do not treat this as reproducing
work; drop it if a future sighting under the same conditions also fails
to reproduce.

## 1. The exact close-guard error captured

Command: `frob ticket close T-3122` (from
/home/logan/projects/frob/.claude/worktrees/t-3122)

Verbatim stderr/stdout tail:

    ERROR: close failed: T-3122 -- Done report contains disclosure-shaped language ("non-standard Done-report subsection ('Changed')") but no 'Filed:' line names a follow-up ticket -- file a follow-up (`frob ticket new ...`) and add a 'Filed: T-####' line to the Done report naming it, or run `frob ticket done-report T-3122 --why-file PATH` again with the disclosure removed if it does not actually describe cut work
    WARNING: [FAST_EXIT1] 'frob ticket close T-3122' exited with an ERROR (exit=1) in 1658ms
    [REPEATED_FAILURE] 'frob ticket close T-3122' has now failed 3 times in a row

This fired even though `"Changed"` is a member of
`src/frob/tickets/_reporting.py::_TIER_A_GENERATED_SUBHEADINGS` (the
exact exempt-title allowlist `disclosure_shaped_language`'s signal 2
checks against), and the section that triggered it was the tool's OWN
`compose_done_report`/`done-report` auto-generated content, not
hand-authored.

## 2. Non-reproduction

Direct calls to the exact guard functions the CLI close path invokes
(`disclosure_shaped_language`, `filed_followup_tickets`,
`_undisclosed_remainder_reason` in
`src/frob/app/ticket_runner/_close_cmd.py`), run against the on-disk
ticket state right after the failing CLI attempt, both returned clean
(no block). Three subsequent `frob ticket close T-3122` CLI attempts
all timed out (exit 143) under continued host load rather than either
succeeding or re-showing the error.

CONCLUSION: seen once, could not reproduce via CLI or direct function
call. A plausible but UNVERIFIED mechanism: a stale/torn sqlite cache
read under concurrent write load (see below) producing a wrong `body`
value or wrong exempt-title comparison exactly once.

## 3. Separate, likely more important finding: sqlite cache lock errors under concurrent `frob check`

Captured in the same window, command `frob check --ticket T-3122`:

    WARNING: frob check: 6 other check(s) already running on this host
    WARNING: cache.connect: unreadable db at .../t-3122/.frob/cache.db, rebuilding: no such table: meta
    WARNING: cache.connect: unreadable db at .../t-3122/.frob/parse-artifacts.db, rebuilding: no such table: meta
    ERROR: main: unhandled exception during dispatch: database is locked
    frob: database is locked

This is a HARD failure (nonzero exit, unhandled exception), not a
warning-and-recover. The immediately-following retry of the identical
command succeeded normally. `fleet_status` independently reports this
level of concurrent-check load (6 on host) as close to ambient here,
not an unusual spike.

This sqlite-lock crash under ORDINARY concurrent-check load is a real
defect on its own regardless of whether the close-guard false-fire
above ever reproduces, and is the most plausible root-cause mechanism
for it if it does recur.

## Do-first if picked up

Try to reproduce BOTH symptoms (the disclosure-shaped-language false
block, and the `database is locked` hard crash) under deliberately
concurrent `frob check`/`frob ticket close` load before doing anything
else. If neither reproduces after a real attempt, drop this with that
reason, per the same T-3131 standard.
