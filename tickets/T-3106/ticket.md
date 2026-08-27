---
id: T-3106
title: Fix fleet_status.py orphan false-positive and add frob process reap command
state: in-progress
kind: feature
origin: human
created: '2026-08-27'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/_cli_parsers
- src/frob/app
- tests/unit/test_app_runners_process.py
- docs/modules/app.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: scripts/fleet_status.py
  reason: 'UPDATE 2026-08-27: the scripts/fleet_status.py half of this ticket is

    DONE -- T-3093 fixed _FROB_CHECK_TOKEN_RE (replaced with

    _is_live_check_cmdline, whole-token match) and confirmed live that the

    ORPHANED FORKSERVERS line no longer false-positives on "python -m frob

    check ..." launchers. Remaining scope: only the "frob process reap" CLI

    command (parser + dispatch wiring), not the fleet_status.py fix.

    '
  actor: logan
  at: '2026-08-27'
- op: add
  glob: tests/unit/test_app_runners_process.py
  reason: 'T-3106: new dedicated test file for the process reap CLI wiring'
  actor: logan
  at: '2026-08-27'
- op: add
  glob: docs/modules/app.md
  reason: 'T-3106: process_runner.py''s frob:doc anchor cites app.md#runners, matching
    ops_runner.py''s own existing convention'
  actor: logan
  at: '2026-08-27'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-3072 diagnosed the "still-leaking forkservers" report as substantially a
MEASUREMENT ARTIFACT: scripts/fleet_status.py's own ancestry classifier
(_FROB_CHECK_TOKEN_RE = re.compile(rb"(?:^|/)frob\x00")) never matches
"python -m frob check ..." (the fleet's dominant invocation shape under
"uv run"), because "^" only anchors the WHOLE cmdline blob's start, not
each NUL-delimited argv token. Confirmed live 2026-08-27: two running
"python -m frob check ..." launchers (pids 707388, 823429) were both
alive, yet fleet_status.py reported all 9 of their descendant forkservers
as ORPHANED.

T-3072 fixed the equivalent, in-scope copy inside
src/frob/process/_reap.py (_is_live_check_process, a whole-token
classifier; _forkserver_root_is_live_check, T-2818's multi-hop ancestry
walk; reap_orphaned_forkservers now uses both) and also fixed a THIRD
copy of the same broken regex that count_running_checks/
_is_frob_check_process carried in that same file. scripts/fleet_status.py
itself is OUT of T-3072's scope (src/frob/process/_reap.py only).

WHAT IS WANTED (two independent pieces)
1. scripts/fleet_status.py's ORPHANED FORKSERVERS line: fix
   _FROB_CHECK_TOKEN_RE the same way (whole-token match, not `(?:^|/)`
   anchored regex), or better, delete fleet_status.py's own
   _all_process_ppids/_forkserver_root_is_live_check/_live_check_pids and
   have it import and call frob.process._reap's new, corrected versions
   instead (frob.process is an importable package; scripts/ already
   imports plenty from it) -- eliminating the duplicate this ticket found
   rather than fixing it a fourth time somewhere else later. This is
   squarely in T-3093's own scope and T-3093's own body already names the
   ORPHANED FORKSERVERS line as an audit candidate -- do it there.
2. Expose reap_orphaned_forkservers as a first-class, on-demand CLI
   command (e.g. "frob process reap") rather than only a side effect of
   "frob check" startup -- needs a new subcommand parser + dispatch,
   outside src/frob/process/_reap.py's own scope (T-3072's ticket scope).
   Wire it under whatever src/frob/_cli_parsers/ + src/frob/app/ module
   already hosts sibling process/maintenance subcommands.

ACCEPTANCE
- scripts/fleet_status.py's ORPHANED FORKSERVERS line does not
  false-positive on a "python -m frob check ..." launcher, verified live
  the same way T-3072 did (a real running "frob check" process, its
  descendant forkserver confirmed NOT reported orphaned).
- "frob process reap" (or equivalent) exists, calls
  frob.process.reap_orphaned_forkservers, and its own help text/docs make
  clear it is safe under concurrency (never touches a live-parented
  forkserver).
