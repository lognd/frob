---
id: T-3131
title: 'UNCONFIRMED-ONCE: close disclosure-guard false-fire on exempt Changed subsection'
state: dropped
kind: bug
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
- src/frob/tickets/_reporting.py
- src/frob/app/ticket_runner/_close_cmd.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 6817e7e33f1b7593d8e2fa5012a7290381c0ab22
---
UNCONFIRMED-ONCE: `frob ticket close` disclosure-shaped-language guard
(`_undisclosed_remainder_reason` in
src/frob/app/ticket_runner/_close_cmd.py, backed by
`disclosure_shaped_language` in src/frob/tickets/_reporting.py) was
observed to refuse a close citing a "non-standard Done-report subsection
('Changed')" -- but `"Changed"` IS a member of the code's own
`_TIER_A_GENERATED_SUBHEADINGS` exempt-title allowlist, and the section
that triggered it was the tool's own `done-report`-generated content
(compose_done_report's own "### Changed" diffstat block), not a
hand-authored subsection. Seen exactly ONCE, while filing T-3122's close
during heavy concurrent host load (live `frob ticket land T-3115` plus
fleet_status reporting ~6 concurrent `frob check` runs on the host).

## What was captured (verbatim)

Exact error:

    ERROR: close failed: T-3122 -- Done report contains disclosure-shaped language ("non-standard Done-report subsection ('Changed')") but no 'Filed:' line names a follow-up ticket -- ...

The exact done-report.md content in effect at that commit (1466202a4)
had `### Changed`, `### Evidence`, `### Captured claims` -- all three are
tool-generated, all three are members of `_TIER_A_GENERATED_SUBHEADINGS`,
none should have tripped signal 2 of `disclosure_shaped_language`.

## Non-reproduction (this is the important part)

Ran the EXACT functions the CLI close path calls, TWICE, against the
current on-disk ticket state immediately after the failing CLI call:

    from frob.tickets import load_queue
    from frob.tickets._reporting import disclosure_shaped_language, filed_followup_tickets
    q = load_queue(Path('.')).danger_ok
    t = q.tickets['T-3122']
    disclosure_shaped_language(t.body)   # -> None
    filed_followup_tickets(t.body)       # -> []

    from frob.app.ticket_runner._lifecycle import _load_ticket_or_exit
    from frob.app.ticket_runner._close_cmd import _undisclosed_remainder_reason
    t = _load_ticket_or_exit(Path('.'), 'T-3122', verb='close')
    _undisclosed_remainder_reason(Path('.'), t)   # -> None

Both direct calls -- the literal functions `_close()` invokes, called the
same way -- returned clean (no block), both times. Every subsequent CLI
`frob ticket close T-3122` retry (3x) TIMED OUT under continued host load
(exit 143, no output at all) rather than either succeeding or re-showing
the error, so this could not be confirmed to reproduce on demand either
way. Stating this plainly: I have NOT shown this reproduces. I am filing
it because it was genuinely observed once with the exact text above, not
because I have demonstrated it is real.

## Candidate mechanism

T-3130 (filed alongside this one) is an unhandled `database is locked`
sqlite3 crash in `src/frob/graph/cache.py::connect` under the same class
of concurrent-load window, captured in the same session. A stale or
torn cache read racing a concurrent write (T-3130's exact failure mode)
is a plausible mechanism for `load_queue`/`t.body` serving a transiently
wrong value exactly once, which would explain a guard firing on content
that direct re-inspection then shows was never actually a match. This is
speculative, not verified -- flagging the connection so whoever
investigates T-3130 can check whether ticket-queue loading shares any of
the same cache path, and whoever revisits this ticket has the most
likely lead.

## Plan

Do not act on this until/unless it reproduces. If it recurs, capture the
exact error text, the exact ticket body content, and whether T-3130's
cache-lock symptoms are present in the SAME invocation (same command,
overlapping timestamp) -- that would upgrade this from speculative to a
demonstrated causal link. If it does not recur across a reasonable
number of future closes, this can be dropped as noise once T-3130 is
independently confirmed fixed and it still never recurs.

## Drop reason
- 2026-08-27: UNCONFIRMED-ONCE per its own title: re-ran the exact functions the CLI close path calls (disclosure_shaped_language against a Done report carrying only the exempt Changed/Evidence/Captured-claims subheadings) on current main and in this worktree -- both return None, no false-fire. The T-2718 fix that exempts 'Changed' already predates the single observed incident (commit 1466202a4), so the guard code was already correct at observation time, consistent with the ticket's own candidate mechanism: a transient cache read racing a concurrent write (T-3130's exact failure mode, same session, same host-load window). T-3130 (database is locked under concurrent frob check) is now independently confirmed DONE, and no further recurrence has been observed since (including this session's own T-3104 close, which produced a Done report with the identical Changed/Evidence/Captured-claims shape and closed clean). Per the ticket's own plan: drop as noise now that T-3130 is fixed and it has not recurred.
