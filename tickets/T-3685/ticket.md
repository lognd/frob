---
id: T-3685
title: 'CI macOS flake: ticket close sys.exit(1) in archive-force test under load,
  unreproduced on Linux'
state: in-progress
kind: bug
origin: human
created: '2026-09-01'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/test_ticket_runner_archive_force.py
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
## Description

CI run 33582058515 (macOS leg) failed
tests/test_ticket_runner_archive_force.py::TestTicketArchiveForceCLI::test_refuses_without_force_when_a_live_lease_exists
intermittently under load (both legs were fully green in run 33545437868 --
this is a genuine flake, not a hard regression). Distinct root cause from
T-3684 (filed for the ubuntu leg's `load_all` TOCTOU) -- different code
path, different symptom, and this ticket's investigation could not
reproduce it locally, so it is filed as an investigation/repro ticket
rather than a blind fix.

Reported failure: `SystemExit: 1` raised from the test's own
`_make_done_ticket` helper -> `ticket close` ->
`src/frob/app/ticket_runner/_close_cmd.py:1465` (the `sys.exit(1)` in
`commit_ticket_ledger_change`'s error branch, OR the earlier `sys.exit(1)`
at line ~1448 in `transition(...)`'s own error branch -- CI's captured
traceback line number alone does not disambiguate which of the two
`sys.exit(1)` calls in this function fired; needs the full captured
stdout/stderr from a real CI failure, not just the one line quoted in
this drive's brief, to pin down which).

Important: `_make_done_ticket`'s three `ticket_run` calls (new/start/close)
are fully SEQUENTIAL, single-threaded, on one process -- there is no
in-test race the way T-3684's test has one. So this failure is either:

(a) a genuine cross-PROCESS race: something this test's single sequence
    touches that a SIBLING xdist worker's own concurrent `frob`/`git`
    subprocess also touches and can contend/timeout against (candidates:
    `ledger_lock`'s `fcntl.flock`/`msvcrt.locking` on `.frob/tickets.lock`
    -- but that path is per-`tmp_path`-repo, so should not cross workers
    unless something resolves to a shared location; or a `git commit`
    subprocess timing out under heavy CI-runner CPU contention, surfacing
    as `commit_ticket_ledger_change`'s `Err` -> the second `sys.exit(1)`);
    or

(b) a macOS-specific timing/resource difference (slower git/subprocess
    spawn under CI runner load stretches a window that never opens on a
    faster/less-contended box) that this repo's Linux dev environment
    cannot reproduce at all.

## Investigation done (this ticket, no product code touched)

Reproduction attempted per the standard playbook: `tests/test_ticket_
runner_archive_force.py` looped (`-p no:xdist`) 120 times total (6
parallel loop processes x 20 iterations each) while a genuine
`pytest -n 12` full-suite run churned concurrently in the background for
CPU/IO contention -- the exact recipe that reproduced T-3684's race in
~20-50 iterations. Zero failures across all 120 runs, on Linux/WSL.

This does NOT rule out (a) or (b) -- it only establishes the failure
window here is either far narrower than T-3684's, or genuinely tied to
macOS-specific subprocess/filesystem timing this Linux box cannot
manufacture.

## Plan (for whoever picks this up)

1. Get the FULL captured output (not just the one traceback line) from a
   real CI macOS failure of this test -- which of the two `sys.exit(1)`
   sites in `_close_cmd.py` fired, and what `result.danger_err`/
   `committed.danger_err` was, is the load-bearing fact this ticket does
   not yet have.
2. If reproducible on a macOS runner (or a slower/more-contended box):
   loop this test under `-n auto` xdist load on that platform specifically.
3. Root-cause from there -- likely candidates to check first:
   `commit_ticket_ledger_change` (`src/frob/tickets/_leases.py`)'s git
   subprocess timeout under contention, and whether `transition`
   (`src/frob/tickets/_evidence.py`) has any of its own unlocked
   glob-then-read pattern akin to T-3684's finding (same `load_all`/
   `_parse_ticket_file` seam T-3684 just hardened -- if this test's repo
   ever has a sibling ticket dir being touched concurrently by another
   process in real CI, the exact T-3684 mechanism could apply here too,
   but nothing in `_make_done_ticket`'s single-ticket, single-process
   flow creates that scenario on its own).
4. Do NOT weaken the test's `pytest.raises(SystemExit)` assertion or add
   sleeps -- if this is a genuine race, fix it at the layer the race
   lives in, matching T-3684's posture.

## Scope

Left deliberately narrow (investigation-only) since the root cause is not
yet established. Whoever picks this up should widen scope once (a) or (b)
above is confirmed -- likely into `src/frob/tickets/_leases.py`
(`commit_ticket_ledger_change`) and/or `src/frob/tickets/_evidence.py`
(`transition`).
