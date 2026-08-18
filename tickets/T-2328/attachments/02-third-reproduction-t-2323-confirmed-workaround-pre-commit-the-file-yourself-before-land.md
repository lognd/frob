# T-2328 follow-up: workaround confirmed, and it pinpoints the mechanism precisely

## Summary

T-2323's land reproduced the exact same defect a THIRD time (after T-2194
and T-2329), but this occurrence pins down the mechanism precisely
because I could compare two attempts on the SAME worktree, same ticket,
same file:

- **Attempt 1** (edit made, left UNCOMMITTED in the worktree, `frob
  ticket land T-2323` invoked): land's own pre-land pipeline silently
  reverted `design/frob.strata` back to main's content -- confirmed by
  re-inspecting the file after the (separately, correctly) failing
  BUG002 refusal: my two capability-grant lines were simply gone, with
  no diff against `HEAD`, and the "wip: pre-land snapshot" commit never
  touched the file at all.
- **Attempt 2** (same edit re-applied, this time `git add design/frob.
  strata && git commit` run BY ME in the worktree BEFORE calling `frob
  ticket land T-2323` again): the land succeeded, and `design/frob.
  strata` WAS included in the final landed commit
  (a09991a89cc2abb5b6144a6ef8b30d4734540324, `git show --stat` lists it
  explicitly). Confirmed present on main afterward.

## What this proves

The revert is NOT applied to already-committed content in the landing
branch -- it specifically targets **uncommitted working-tree changes** to
`design/frob.strata` at some point in land's pre-merge pipeline (between
worktree entry and the "wip: pre-land snapshot" commit). Once the same
edit is a real commit on the ticket's own branch instead of loose
working-tree state, land carries it through untouched.

This narrows the search space a lot: whatever code path is issuing the
"SKIPPED SYS100 design/frob.strata:0 -- design/frob.strata is under
T-2303's live lease" warning is not just skipping ITS OWN write -- it is
running something equivalent to `git checkout -- design/frob.strata` (or
`git restore`) against the WORKING TREE specifically, before the wip
snapshot ever runs, discarding whatever the agent had pending there. A
committed change is invisible to a working-tree-level restore, which is
exactly why attempt 2 survived.

## Recommended fix shape (sharpened from the earlier note, still not
## attempted -- _land_cmd.py is contended)

Whatever helper implements the "leave `design/frob.strata` untouched
because of T-2303's lease" behavior should, at minimum, `git diff
--quiet -- design/frob.strata` (or equivalent) BEFORE doing anything
destructive to it, and refuse loudly (not silently discard) if the
landing ticket's own worktree has real, uncommitted, in-scope edits to
that file. Ideally: commit the file's current state (via the same
mechanism the wip-snapshot step already uses for every OTHER file)
before any lease-driven restore runs, so "restore" only ever means
"leave the ticket's own already-recorded intent alone" and never
"silently throw away work that was never given a chance to be recorded."

## Practical workaround for anyone landing a design/frob.strata edit
## before this is fixed

`git add design/frob.strata && git commit` the change directly in the
worktree BEFORE invoking `frob ticket land`. This was reproduced working
twice in this same session (T-2323's second attempt).
