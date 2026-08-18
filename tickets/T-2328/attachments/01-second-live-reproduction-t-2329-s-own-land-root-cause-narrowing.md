# T-2328 follow-up: second live reproduction, root-cause narrowed (T-2329's own land)

Written immediately after observing this a second time, while still fresh
in this session -- not reconstructed from memory.

## What happened

T-2329 (the direct fast-follow filed to re-apply T-2194's dropped
design/frob.strata capability grant) hit the EXACT SAME defect on its own
land. `git show <T-2329 wip commit> --stat` shows only `rapid-debt.jsonl`
-- design/frob.strata is absent, even though I had edited it on disk in
the T-2329 worktree well before land ran (verified working, `pytest`
passing, `git status --porcelain` showed it modified right up until I
invoked `frob ticket land`).

## Root cause narrowed further than the original T-2328 body

Unlike T-2194 (where I could not tell whether the file was dropped by the
WIP-commit step or reverted earlier), this time I checked the worktree's
OWN `wip: pre-land snapshot for T-2329` commit directly:

    git show 6bfcdc4f5 --stat
    rapid-debt.jsonl | 1 +
    1 file changed, 1 insertion(+)

`design/frob.strata` was ALREADY back to unmodified (matching main) by
the time the wip-snapshot commit was made -- i.e. something upstream of
the generic "absorb uncommitted worktree changes into the wip commit"
step actively reverted (not merely skipped staging for) my edit to that
one file.

The land log's own narrative, in order, both times (T-2194's land and
T-2329's land):

    WARNING: tier-a fixes: SKIPPED SYS100 design/frob.strata:0 --
    design/frob.strata is under T-2303's live lease
    (repeated 7x)
    ...
    ticket land: T-2329 pre-land Tier-A fixes applied 1 fix(es)

This is the smoking gun: the SYS100 Tier-A-fix codepath for
design/frob.strata treats "this file is under another ticket's live
lease" as a reason not just to skip ITS OWN auto-write to the file (the
documented, correct behavior -- Tier-A must not write a file another
ticket has leased), but ALSO discards this ticket's own prior, in-scope,
already-on-disk edit to that same file -- most likely via a `git
checkout HEAD -- design/frob.strata` (or equivalent restore-from-index/
HEAD) issued as a defensive "leave this leased file untouched" guard,
without distinguishing "untouched by MY OWN auto-fix" from "untouched,
full stop, even reverting the calling ticket's legitimate pre-existing
edit". The bug is conflating those two meanings of "untouched".

## Why the lease looked live both times despite being reportedly cleared

Both lands showed the SAME "T-2303's live lease" message, on TWO
separate ticket lands, roughly 45+ minutes apart (T-2194's land ~00:05
UTC, T-2329's land ~00:51 UTC). By T-2329's land, T-2303's own ticket
state had been narrowed to an EMPTY scope on its own worktree (per
`tickets/T-2303/ticket.md` in `.claude/worktrees/t-2303`, confirmed
before this land ran) -- yet the SYS100 skip-check land uses evidently
still resolves `design` as leased by T-2303. This strongly suggests the
skip-check is NOT reading T-2303's live, current lease/scope at land
time -- it may be reading something stale (a cached scope snapshot from
when T-2303 still declared `design` broadly, or resolving "design" as a
directory-prefix match against T-2303's ORIGINAL scope entry rather than
its current one). Whoever fixes T-2328 should instrument exactly what
data source that "is under T-2303's live lease" message reads from
(likely in `frob.tickets._leases` or a scope-collision helper called
from the Tier-A SYS100 fixer in `_land_cmd.py`) and confirm whether it
is keyed on a stale read.

## Recommended fix shape (not attempted -- _land_cmd.py is contended)

The two behaviors need to be separated:
1. Tier-A's own SYS100 auto-fix write to a leased file: correctly
   skipped, as today.
2. The generic wip-snapshot step that absorbs uncommitted worktree
   changes into land's pre-land commit: must NEVER exclude or revert a
   file that is genuinely inside the landing ticket's OWN declared
   scope, regardless of what Tier-A's own unrelated auto-fix decided to
   skip. If (1) and (2) currently share a single "is this file
   touchable" check, that is the coupling to break.

## Evidence this is reproducible, not a one-off

Two independent lands (T-2194, T-2329), same file, same message, same
silent-drop shape, ~45 minutes apart, with T-2303's own worktree-local
scope already empty by the second occurrence. Treat as a hot path, not
edge-case flakiness.
