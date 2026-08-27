# Captured evidence: close-guard false-fire on T-3122 (unconfirmed, seen once)

Captured 2026-08-27, during series BT (T-3122 implementation), while a
concurrent `frob ticket land T-3115` and heavy fleet `frob check` load
(fleet_status: 6 concurrent checks on host) were running.

## 1. The exact close-guard error captured

Command run (from /home/logan/projects/frob/.claude/worktrees/t-3122):

    frob ticket close T-3122

Exact stderr/stdout tail (verbatim):

    ERROR: close failed: T-3122 -- Done report contains disclosure-shaped language ("non-standard Done-report subsection ('Changed')") but no 'Filed:' line names a follow-up ticket -- file a follow-up (`frob ticket new ...`) and add a 'Filed: T-####' line to the Done report naming it, or run `frob ticket done-report T-3122 --why-file PATH` again with the disclosure removed if it does not actually describe cut work
    WARNING: [FAST_EXIT1] 'frob ticket close T-3122' exited with an ERROR (exit=1) in 1658ms; it did NOT do the work you may think it did -- a fast failure is not a fast success.
    [REPEATED_FAILURE] 'frob ticket close T-3122' has now failed 3 times in a row with no successful run in between -- this looks stuck, not progressing; re-running the identical command is unlikely to help.

This fired even though `"Changed"` is a member of
`src/frob/tickets/_reporting.py::_TIER_A_GENERATED_SUBHEADINGS` (the exact
exempt-title allowlist `disclosure_shaped_language`'s signal 2 checks
against), and the section that triggered it (below) was the tool's own
`compose_done_report`/`done-report` auto-generated content, not hand-authored.

## 2. The exact ticket state (commit) the failing close ran against

The done-report.md content at the time of the LAST failing close attempt
(commit 1466202a4, "chore(tickets): record evidence for T-3122" -- this
is BEFORE the source fix commit 391a17594 and before the final
"chore(tickets): T-3122 Done report" commit 78531ecad):

    ## Done report

    Evidence:
    tests/test_refactor.py::TestRunSplit::test_split_carries_forward_imports_moved_body_needs
    (confirmed FAILING at the parent commit before the fix, with
    NameError: name 'StrEnum' is not defined reproduced via a real
    subprocess import of the split's own output; passes after the fix)
    tests/test_refactor.py -- full file, 119 passed
    frob test --base main -- touched-set selection, exit=0

    Filed: none

    Gates: ruff-check/ruff-format/ty clean on the two touched source files
    (src/frob/refactor/_scan.py, src/frob/refactor/_split.py); frob check
    --ticket T-3122 and --delta both show only pre-existing repo-wide
    findings unrelated to this ticket's two-file scope (no baseline is
    stamped in this worktree, so --delta fell back to showing everything).

    ### Changed
    ```
     docs/commands/refactor.md     |  14 +++++
     src/frob/refactor/_scan.py    | 119 +++++++++++++++++++++++++++++++++++++++++-
     src/frob/refactor/_split.py   |  17 ++++++
     tests/test_refactor.py        |  54 +++++++++++++++++++
     tickets/T-3122/done-report.md |  28 ++++++++++
     tickets/T-3122/ticket.md      |   6 ++-
     6 files changed, 236 insertions(+), 2 deletions(-)
    ```

    ### Evidence
    - `tests/test_refactor.py::TestRunSplit::test_split_carries_forward_imports_moved_body_needs` (pytest node id, verified passing when recorded)

    ### Captured claims
    - tests: 1 passed (from 1 evidence id(s))
    - gates: 93 error(s), 696 warning(s), 862 waived
    - error-findings: ARCH103@... [truncated -- full list was ~100 rule@path entries, repo-wide, none touching src/frob/refactor/_scan.py or _split.py]

## 3. Non-reproduction: direct function-level calls returned None (no block)

Ran the EXACT functions the CLI close path calls, twice, against the
current on-disk ticket state, after the failing CLI attempt:

    python3 -c "
    from pathlib import Path
    from frob.tickets import load_queue
    from frob.tickets._reporting import disclosure_shaped_language, filed_followup_tickets
    q = load_queue(Path('.')).danger_ok
    t = q.tickets['T-3122']
    print(disclosure_shaped_language(t.body))
    print(filed_followup_tickets(t.body))
    "
    # -> None
    # -> []

    python3 -c "
    from pathlib import Path
    from frob.app.ticket_runner._lifecycle import _load_ticket_or_exit
    from frob.app.ticket_runner._close_cmd import _undisclosed_remainder_reason
    t = _load_ticket_or_exit(Path('.'), 'T-3122', verb='close')
    print(_undisclosed_remainder_reason(Path('.'), t))
    "
    # -> None (this IS the exact guard function+call the CLI close path uses)

Both direct calls, run identically to how `_close()` in
src/frob/app/ticket_runner/_close_cmd.py invokes them, returned no block.
Every SUBSEQUENT `frob ticket close T-3122` CLI attempt (3x) timed out
(exit 143, terminated at the 200s/540s wrapper budget, no output at all --
not even a fresh reproduction of the error) rather than either succeeding
or re-showing the error, under continued heavy host load.

CONCLUSION: seen once, could not reproduce on demand via either the CLI
(subsequent attempts timed out under load, never completed) or via direct
python calls to the exact guard functions (both returned clean). Genuinely
unconfirmed. A plausible mechanism (not verified): a stale/failed sqlite
cache read under concurrent write load (see part 4 below) producing a
wrong `body` value or wrong exempt-title comparison exactly once.

## 4. Separate, likely more important finding: sqlite cache lock errors under concurrent `frob check`

Captured during the SAME window (concurrent T-3115 land + fleet checks),
command: `frob check --ticket T-3122` (also independently reproduced
error text via `frob check --delta --ticket T-3122` moments later, this
one recovered/rebuilt rather than hard-failing):

    WARNING: frob check: 6 other check(s) already running on this host -- see `scripts/fleet_status.py` for swap/load before dispatching more (T-2473, advisory only -- this check is not deferred)
    WARNING: cache.connect: unreadable db at /home/logan/projects/frob/.claude/worktrees/t-3122/.frob/cache.db, rebuilding: no such table: meta
    ...
    WARNING: cache.connect: unreadable db at /home/logan/projects/frob/.claude/worktrees/t-3122/.frob/parse-artifacts.db, rebuilding: no such table: meta
    ...
    ERROR: main: unhandled exception during dispatch: database is locked
    frob: database is locked

This is a HARD failure (nonzero exit, "unhandled exception during
dispatch"), not a warning-and-recover -- the FIRST `frob check --ticket
T-3122` invocation in this session died outright with `database is
locked` after the two "unreadable db ... rebuilding: no such table: meta"
warnings on cache.db and parse-artifacts.db. The immediately-following
retry of the same command succeeded normally. This happened while
`fleet_status` was reporting 6 concurrent `frob check` runs on the host,
plus a live `frob ticket land T-3115` in the shared root.

Corroborating signal from the coordinator: `fleet_status` independently
reports CONCURRENT CHECKS: 6 on this host even during an otherwise-quiet
window, so this is not a one-off level of contention -- it is close to
ambient here.

This is filed as the higher-priority candidate ticket once the land
window clears: an unhandled `database is locked` crash under ordinary
(not even unusual) concurrent-check load in a per-worktree sqlite cache
(cache.db / parse-artifacts.db) is a real defect regardless of whether
the close-guard false-fire above ever reproduces, and is a plausible
root-cause mechanism for it (a torn/stale cache read serving a wrong
`Ticket.body` or wrong comparison result exactly once under the same
contention).
