## Done report

Reproduced first: with a symbol carrying `# frob:ticket T-0001` and
`T-0001` set to `state: done`, `_bound_to_open_ticket` only checked
`ticket.state in _OPEN_STATES` -- DONE is explicitly excluded from
`_OPEN_STATES` -- so the edge stopped covering the symbol the instant the
ticket closed. COV002 (`_cov002_check_symref`) then fired a hard error on
every symbol still carrying that now-dead edge, with no other account for
the change, regardless of whether the close and the symbol edit are part
of the very same uncommitted diff. That is the catch-22: `frob ticket
close` requires evidence that the change exists, but closing immediately
un-covers the still-uncommitted change it just closed against.

Root cause: `_bound_to_open_ticket` (src/frob/gates/__init__.py) had no
notion of "this DONE transition and this symbol edit are landing
together." Fix: added an optional `diff` parameter -- a ticket in `DONE`
state now also counts as covering if `tickets.md` itself is a touched file
in the same `diff` (the close's own write to the ledger). This is a
same-diff grace window, not a general DONE-ticket exemption: once the
close lands as its own separate commit, `tickets.md` drops out of the diff
base again and a DONE ticket's edge stops covering, so a genuinely later
and unrelated touch to the same symbol is still caught by COV002 exactly
as before (locked by
`test_cov002_done_ticket_without_grace_still_fires`).

Changed:
- src/frob/gates/__init__.py::_bound_to_open_ticket -- diff param, DONE +
  tickets.md-in-diff grace window
- src/frob/gates/__init__.py::_covered_by_strata_module -- threads diff
  through to _bound_to_open_ticket
- src/frob/gates/__init__.py::_cov002 -- passes diff into
  _cov002_check_symref
- src/frob/gates/__init__.py::_cov002_check_symref -- diff param, passes
  through to both coverage checks
- docs/modules/gates.md -- COV002 table row + new design-decision bullet
  documenting the grace window and why it does not weaken genuine gaps
- tests/test_gates.py::TestCoverageGate -- two new litmus tests (below)

Evidence:
- tests/test_gates.py::TestCoverageGate::test_cov002_done_ticket_covers_own_closing_diff
  (the catch-22 scenario: DONE ticket + tickets.md in diff -> COV002 clean)
- tests/test_gates.py::TestCoverageGate::test_cov002_done_ticket_without_grace_still_fires
  (the genuine-gap regression lock: DONE ticket + tickets.md NOT in diff ->
  COV002 still fires)
- Full `tests/test_gates.py` (136 collected, all pass) and `make coverage`
  (full suite green) run clean.

Gates: `uv run frob check --stamp-baseline` (1 pre-existing violation,
unrelated to this change) then `uv run frob check --delta` after `make
coverage` -> `gates 0/1 new  0 errors, 0 warnings, 204 waived`, all tool
summary rows `pass`. `ruff check`/`uv run ruff check`, `ruff format
--check`/`uv run ruff format --check`, and `uv run ty check` all clean on
the touched files.

Filed: none.

Not closing -- leaving in-progress for reviewer per the review-gated flow.

### Addendum: reviewer-found bypass fixed

Reviewer reproduced a bypass in the grace window above: `_bound_to_open_ticket`
only checked (a) the bound ticket is `DONE` and (b) `tickets.md` is touched
*somewhere* in the diff -- it never verified that THIS bound ticket's own
close is what's in the `tickets.md` hunk. A symbol `frob:ticket`-bound to
any old, already-`DONE` ticket rode along on an unrelated `tickets.md` edit
(e.g. a different ticket closing, or any other ledger touch) and silently
passed COV002 with zero real coverage. Reproduced: `helper` bound to a
stale `DONE` `T-0001`, diff touches `src/a.py` + a `tickets.md` hunk that
only contains `T-0002`'s marker -> COV002 incorrectly clean pre-fix.

Fix: replaced the "`tickets.md` touched anywhere" check with
`_ticket_marker_in_diff_hunk(root, diff, ticket_id)`
(src/frob/gates/__init__.py) -- it reads `tickets.md` from `snapshot.root`
and confirms THIS ticket's own `<!-- ticket:T-#### -->` marker line falls
inside one of the diff's `tickets.md` hunk spans, not merely that some hunk
exists in that file. Grace now requires the specific ticket's own close to
be present in the diff's ledger hunk; a stale `DONE` ticket whose marker is
outside every touched span (or whose file doesn't exist yet, or when
`tickets.md` isn't touched at all) gets no grace and COV002 fires as normal.

Changed (addendum):
- src/frob/gates/__init__.py::_bound_to_open_ticket -- grace condition now
  calls `_ticket_marker_in_diff_hunk` instead of the bare
  `"tickets.md" in _touched_files(diff)` check
- src/frob/gates/__init__.py::_ticket_marker_in_diff_hunk -- new helper,
  reads `tickets.md` at `snapshot.root` and checks the bound ticket's
  marker line falls within a touched hunk span
- tests/test_gates.py::TestCoverageGate::test_cov002_done_ticket_covers_own_closing_diff
  -- updated to write a real `tickets.md` via `write_ticket` and target the
  hunk span at the actual marker line, so the grace path is exercised for
  real instead of by an unchecked `(1, 1)` stub span
- tests/test_gates.py::TestCoverageGate -- new
  `_marker_line` helper (finds a ticket's marker line number in
  `tickets.md` for building a precise `Hunk` span)
- tests/test_gates.py::TestCoverageGate::test_cov002_stale_done_ticket_unrelated_tickets_md_touch_still_fires
  -- new abuse-case regression: stale `DONE` T-0001 bound to `helper`,
  diff's `tickets.md` hunk only covers unrelated `DONE` T-0002's marker ->
  COV002 still fires. Confirmed this test FAILS on the pre-addendum code
  (`git stash` of the `_bound_to_open_ticket`/`_ticket_marker_in_diff_hunk`
  edit, reproducing the bypass) and PASSES after.

Evidence (addendum): `uv run pytest tests/test_gates.py -q -k
TestCoverageGate` all 25 green (23 pre-existing + this addendum's new
test), including the two original T-0214 litmus tests still passing
unmodified in behavior (`test_cov002_done_ticket_without_grace_still_fires`
untouched; `test_cov002_done_ticket_covers_own_closing_diff` updated to use
a real ledger file, same assertion). `uv run pytest tests/test_gates.py -q`
full file green. `uv run ruff check`, `uv run ruff format --check`, `uv run
ty check` all clean on `src/frob/gates/__init__.py` and
`tests/test_gates.py`. `uv run frob check --only coverage` clean, 0
errors/0 warnings.

Gates (addendum): all green per above. Still not closing -- reviewer.
