---
id: T-1732
title: frob ticket land structurally cannot carry a cross-ticket ledger edit forward
  (splice_ledger tiebreak drops it)
state: queued
kind: bug
origin: human
created: '2026-08-07'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_land_ledger_merge.py
- src/frob/tickets/_land_squash.py
- tests/test_ticket_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
## Description

`frob ticket land`'s squash-apply carries `tickets.md` forward via
`splice_ledger` (`frob.tickets._land_ledger_merge`), which merges "at the
ticket-id level, keeping the newest state per section" (`_newer`). This
structurally drops a legitimate edit to a DIFFERENT ticket's own section
made in the same worktree, whenever that edit does not change state rank
or Done-report presence -- an evidence-list value change (e.g. `frob
ticket evidence <other-id> --replace OLD NEW`) is invisible to `_newer`'s
comparison heuristic, so the tiebreak falls through to whichever side it
defaults to (observed: main's side wins), silently discarding the edit.

Observed twice in the same session (2026-08-06/07): while working T-1679,
a coordinator-requested fix rebound T-1637's (a DONE, unrelated ticket)
evidence citations to match a rename made by T-1679's own diff. That
rebind was committed in the worktree and verified clean locally, but
`frob ticket land T-1679`'s squash never carried it -- main kept T-1637's
stale evidence, later surfacing as T-1714's own regression (2 COV003
findings). T-1714 was filed and landed specifically to re-fix this, its
Done report explicitly claiming "This ticket's own land is what actually
carries it" -- but a `git show main:tickets.md` check immediately after
T-1714's land showed T-1637's block STILL unchanged: T-1714's land
carried T-1714's OWN section (state/evidence) but again dropped the T-1637
section edit, for the identical reason.

This is a real structural gap, not a one-off: `frob ticket land <id>`
cannot carry a legitimate edit to a ticket OTHER than `<id>` forward, no
matter which ticket "sponsors" the edit or how many times it is redone,
because `splice_ledger`'s per-section merge only ever compares state-rank/
report-richness, never raw content, and always resolves a tie toward one
side (main) regardless of which side's content is actually newer/correct.

## Impact

Any legitimate cross-ticket ledger correction (evidence rebinds after a
rename, scope corrections discovered while working a different ticket,
citation fixes) made from a worktree is currently **unlandable** through
the normal `frob ticket land` path -- it will always look like it worked
locally and always silently vanish from main. The workaround used twice
(re-apply the edit, hope a DIFFERENT ticket's land carries it) does not
work and should not be relied on again; it burned two ticket-cycles
(T-1714, this investigation) without actually fixing the regression.

## Plan (sketch)

- Extend `_newer`'s (or `splice_ledger`'s) comparison to detect a genuine
  CONTENT difference between `ours`/`theirs` for a ticket's section, not
  only state-rank/report-richness -- when one side differs from `base_text`
  (the true merge-base, already threaded through per T-1154) and the other
  does not, the side that changed should win, independent of state rank.
- Alternatively/additionally: give `frob ticket land` an explicit way to
  declare "this land also carries a correction to ticket X's own section"
  (mirroring `--allow-cross-ticket`'s disclosure model for CODE passengers,
  but for ledger sections specifically) so a deliberate cross-ticket ledger
  fix has a sanctioned, verified path instead of hoping the heuristic
  happens to pick the right side.
- Regression coverage: a worktree edits ticket B's section (evidence only,
  no state change) while landing ticket A; after `frob ticket land A`,
  `git show main:tickets.md` must show ticket B's edit present, not
  reverted to main's stale prior content.

Filed while working T-1706 (the T-1670 part-2 split), after discovering
T-1714's land had not actually fixed what it claimed to fix.