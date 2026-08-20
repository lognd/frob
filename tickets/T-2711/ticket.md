---
id: T-2711
title: A passenger ticket's content lands via --allow-cross-ticket while its own ledger
  state stays non-terminal, leaking its scope lease
state: queued
kind: bug
origin: human
created: '2026-08-20'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_land.py
- src/frob/tickets/_land_verify.py
- docs/modules/tickets-landing.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/app/ticket_runner/_land_cmd.py
  reason: narrowing to avoid T-2715's live lease collision -- the T-2711 fix belongs
    in _check_already_landed (_land.py), not _land_cmd.py
  actor: logan
  at: '2026-08-20'
- op: add
  glob: docs/modules/tickets-landing.md
  reason: documenting the content-diff fix for _check_already_landed
  actor: logan
  at: '2026-08-20'
body_changes:
- mode: append
  reason: cross-reference T-2678/T-2679 as the same mirror-copies-too-much pattern
    (coordinator-corroborated), document the TICK011 friction explicitly
  actor: logan
  at: '2026-08-20'
  old_length: 3468
  new_length: 6670
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Real incident, three independent instances in one worktree
(2026-08-19/20): `--allow-cross-ticket` lets a series worktree's SIBLING
tickets ride onto main as passengers inside the FIRST ticket's land
commit (T-1618's own documented behavior -- this is not the bug). The
bug is what happens to the passenger's own ledger entry afterward:

- T-1549 landed at 8a27d7828 carrying T-2141's `_cross_ticket_
  carried_paths` + its 177-line test file + T-2141's own `done-report.md`
  onto main as an undisclosed-turned-disclosed passenger (per T-2141's
  own new disclosure). T-2141's `state:` stayed `in-progress` on main.
- The same land ALSO carried T-2303's telemetry.py/_land_cmd.py/_new.py
  PERF004/PERF005/PERF008 fixes onto main. T-2303's `state:` also stayed
  `in-progress` on main.
- `git diff main -- <passenger's own scope files>` was EMPTY for both
  tickets afterward -- their own code was already shipped, so every
  subsequent `frob ticket land <passenger>` attempt was a structural
  no-op: no new content to merge, yet the command still ran the full
  merge/gate/claims-reverify pipeline, still could refuse
  (BUG002/ClaimDivergence) or time out under fleet contention, and
  NEVER reported "there is nothing left to land, only a state to flip".
  Three attempts and two rounds of "send me the verbatim error" were
  spent on T-2141 alone before this was understood.
- T-2303 additionally LEAKED ITS LEASE: after T-2141's land ran
  `--finish` and the series worktree was (at one point) reported
  removed, T-2303's still-`in-progress` state held a lease on
  `telemetry.py`/`_land_cmd.py` with no worktree behind it --
  `fleet_status` reported `T-2303 -> <no worktree>  [LEAK]`, and it
  blocked a SEPARATE agent (T-2694, the telemetry split) from touching
  `telemetry.py` at all, even though T-2303's own code was already
  merged and inert.

This is the mirror image of T-2679 (state flips to a terminal value with
ZERO code on main -- the ledger claims work that never shipped). Here
the CONTENT ships and the STATE never reaches a terminal value -- the
ledger UNDERCLAIMS work that already shipped. Both are the same root
class: the ledger and the tree disagreeing, invisible unless checked
separately (`git log --grep`/`state:` field vs `git grep`/`git show
--stat` on the actual symbol). Neither symptom is visible from a single
signal -- you have to check content and state independently to catch
either direction.

The actual fix that resolved this by hand, twice, for reference: run
`frob ticket close <passenger-id>` from the worktree that holds its
lease (flips state to `done` in the worktree branch, which the T-2563
body/scope mirror machinery then propagates onto main's own ticket.md
as a side effect of the NEXT `frob ticket body`/`scope` write against
that ticket -- not automatically, not immediately, and not via any
explicit "sync state" step). A land attempt against an already-landed
passenger should recognize "nothing to merge, only a state transition
needed" and either auto-close+mirror cleanly or say exactly that in its
refusal, instead of running the full pipeline and returning whatever
unrelated gate happens to fire first (BUG002 confirmatory-only, in both
observed cases here -- itself a RESULT of the passenger-carry, not an
independent problem).

Cross-reference: T-2679 (inverse shape -- state terminal, content
absent). Cross-reference: T-2141 and T-2303 themselves, the two ticket
ids this incident happened to.


UPDATE (coordinator-corroborated, 2026-08-20): the T-2303 mirror
mechanism this ticket documents above is NOT an isolated oddity -- it is
the third confirmed instance of the same defect class: T-2563's ledger
mirror copying MORE than the verb that triggered it intended to write.

- T-2678: the mirror copied a WHOLE archived-ticket directory on an
  unrelated body write, corrupting archived-ticket content that write
  never touched.
- T-2679: state reaches a terminal value with ZERO code on main (the
  ledger OVERCLAIMS work that never shipped).
- This ticket (T-2141/T-2303 passenger case): a ledger state transition
  (`state: done`, set by `frob ticket close` in a worktree) reached MAIN
  with no explicit sync step at all -- it rode along as a side effect of
  a LATER, UNRELATED `frob ticket body --append-file` write (the BUG002
  waiver), because T-2563's body-mirror copies the WHOLE worktree
  ticket.md file, `state:` field included, not just the field the
  triggering verb actually changed. The ledger UNDERCLAIMS-then-silently-
  catches-up: main showed `state: in-progress` for a real span of time
  after the code had already shipped, and then flipped to `done` with no
  operator-visible "land" or "sync" event at all -- just an unrelated
  body edit's own mirror commit.

Pattern, not anomaly: every one of the three mirrors more than the
triggering verb's own field(s) -- T-2678 copies a whole directory for a
body edit, this ticket's case copies a whole ticket.md's `state:` field
for a body edit, T-2679 is the same class from the opposite direction
(a transition landing with no content backing it). The fix likely
belongs at the mirror's own boundary (T-2563's `_ledger_mirror`):
narrow every mirror write to the SPECIFIC field(s) the triggering verb
changed, never a whole-file/whole-directory copy, the same fix T-2570
already applied for done-report.md specifically (excluding it from the
mirror's copy set) -- but that exclusion is per-filename, not per-field,
so it does not close this shape (state: rides inside ticket.md itself,
the file scope/body/state all share).

Also: `frob ticket close` refused twice in this same incident (T-2141
and T-2303 both) with a TICK011-shaped error -- "Done report contains
disclosure-shaped language ('non-standard Done-report subsection
(\'Changed\')') but no 'Filed:' line names a follow-up ticket" --
triggered by the auto-generated `### Changed` section `frob ticket
done-report` ITSELF writes into every Done report (a `git diff --stat`
block, T-1000-era machinery). The gate cannot tell its own tool's
routine output from hand-typed disclosure prose describing cut work,
so every ticket with a genuine `### Changed` section and no separately-
filed follow-up hits this, regardless of whether anything was actually
cut. Worked around twice by appending a `Filed:` line naming a real,
already-filed follow-up each time -- but a ticket with a `### Changed`
section and genuinely NO follow-up to file has no clean escape from
this loop today. Either exempt the auto-generated `### Changed` header
specifically from the disclosure-language heuristic, or teach the
heuristic to recognize IT'S OWN generator's fixed section names.
