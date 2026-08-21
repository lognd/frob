## Done report

Changed:
- docs/guides/agent-playbook.md section 1 step 0 -- this WAS the source of
  the broken guidance: its own text read `ps aux | grep "ticket land" |
  grep -v grep` must be empty as the pre-merge land-in-flight check. A
  prior pass at this ticket's Done report claimed the playbook "did NOT
  recommend a pgrep form anywhere" -- that claim was wrong; the form was
  present verbatim in the one place every agent reads first (section 0
  step 0 of the warm-up sequence, run before every `git merge main`).
  Replaced it with a pointer to `uv run python scripts/fleet_status.py`
  and its `LANDS IN FLIGHT: N` line, plus an explicit statement that
  hand-rolled `ps`/`pgrep` self-matches and can never reliably reach
  zero while anyone is polling.
- docs/guides/agent-playbook.md section 13 (T-1344 CORRECTION paragraph)
  -- generalized the existing single-measurement footnote (which only
  warned against one specific `ps aux | grep -c` form) into a standing
  rule that EVERY hand-rolled form is wrong the same way, named
  `fleet_status.py` as the authoritative replacement, and added an
  unambiguous statement of the land threshold: FEWER THAN 2 in flight,
  not zero -- to correct the "wait for an idle fleet" misreading the
  ticket names as the dominant source of wasted waiting.
- docs/modules/tickets-landing.md ("Gap 4") -- this gap was marked
  "(partial)" and its own prose proposed a hypothetical `frob
  doctor`-style surface as an unbuilt follow-up. That follow-up already
  shipped as `scripts/fleet_status.py`; corrected the note to CLOSED and
  pointed at it instead of leaving a stale "not built yet" claim standing
  next to a tool that already answers it.

Investigation (per the ticket's corrected premise -- do not build a
second query):
- Root cause of "why did everyone reach for pgrep": the playbook's own
  warm-up section (read first, every ticket, per section 0 item 0's own
  instruction) told agents to run exactly the broken form. This is not a
  case of missing guidance the tooling already covered elsewhere -- it
  is guidance actively pointing the wrong way, in the single
  highest-traffic section of the file. Fixed above.
- `.claude/hooks/frob-suggest.py`'s `handrolled-fleet-probe` rule already
  nudges toward `fleet_status.py` when `git status --porcelain` is
  combined with `ps aux`/`pgrep`/`git worktree list` in one command --
  the tooling-vs-guidance disagreement the ticket names: the hook already
  pushed the right way while the playbook text pushed the wrong way.
  Left the hook's trigger condition unchanged: broadening it to catch a
  bare land-lock pgrep with no git-status companion is a code change, and
  the ticket's own correction says any code change needs measurement
  first (none taken this ticket).
- `docs/guides/coordinator-scripts.md`'s `pgrep` mention (the T-2475
  land_process_rows section) documents a PAST incident as justification
  for `fleet_status.py`'s own argv-reverification logic -- correct as
  written, no fix needed.
- `tickets/**/*.md` pgrep mentions are historical ticket bodies/
  done-reports (T-1963, T-1999, T-2031, T-2033, T-2475, and archived
  T-1377/T-1779/T-1786/T-1795/T-1806) -- records of what happened, not
  live guidance; left untouched.
- Dispatch briefs themselves (prose the coordinator writes per-dispatch,
  not a tracked file) are outside this ticket's scope to edit directly;
  the fix here is making the playbook -- the thing dispatch briefs are
  supposed to defer to -- correct, so future briefs that say "playbook
  governs" inherit the fix.

Evidence: none applicable -- doc-kind change, no code path touched.
`frob check --json --no-cache --ticket T-2742` (gates only) shows 0
errors attributable to any of the three changed doc regions.

Filed: none.

Gates: `frob check --ticket T-2742` unscoped repo-wide counts show the
same pre-existing debt noted in T-2749's Done report (unrelated to this
ticket, per playbook section 6c's scope-note); 0 new errors attributable
to this ticket's changes.
