## Done report

Changed:
- scripts/wait_for_land_slot.py::probe_unattributed_land_process (new)
- scripts/wait_for_land_slot.py::wait_for_slot (new `unattributed_probe` gate, defaults to the new function)

Evidence:
- tests/unit/test_wait_for_land_slot_unattributed.py::TestProbeUnattributedLandProcess.test_true_when_a_row_has_no_parseable_ticket_id
- tests/unit/test_wait_for_land_slot_unattributed.py::TestProbeUnattributedLandProcess.test_false_when_every_row_has_a_ticket_id
- tests/unit/test_wait_for_land_slot_unattributed.py::TestProbeUnattributedLandProcess.test_false_when_no_rows_at_all
- tests/unit/test_wait_for_land_slot_unattributed.py::TestWaitForSlotUnattributedGate.test_unattributed_land_process_blocks_an_otherwise_free_slot
- tests/unit/test_wait_for_land_slot_unattributed.py::TestWaitForSlotUnattributedGate.test_no_land_at_all_still_returns_free_promptly

Approach: reused T-1619's own belt-and-braces process-scan question ("is
a live `frob ticket land` process running, attributed or not") without
adding a third `/proc` walk, by reading `fleet_status.py`'s own
`land_process_rows()` -- the already-argv-verified (T-2475) raw row list
`land_invocations()` groups-and-filters before this script's text probe
ever sees it. `land_invocations()` deliberately drops any row with no
parseable `T-####` id (T-2193's own fix against a watcher-shell false
positive) -- correct for its own `LANDS IN FLIGHT` purpose, but that
silently dropped exactly the row frob's own T-1619 refusal still catches.
`probe_unattributed_land_process` reads the SAME raw rows one layer
earlier and reports `True` if any lack a parseable ticket id;
`wait_for_slot`'s new `unattributed_probe` parameter (default: this
function) blocks a free-slot verdict unconditionally when it fires,
never subject to `--max-in-flight`, matching T-1619's own unconditional
refusal on this case. Direct Python import of `fleet_status.py` (sibling
script, already ordinary importable Python per `tests/unit/conftest.
_load_script`), not a subprocess -- no frob src import was needed, so
the "if not importable, propose a new home" contingency in the ticket
did not apply.

Positive controls (both directions, both in the new test file):
- `test_unattributed_land_process_blocks_an_otherwise_free_slot`: the
  text probe reads a genuinely free `LANDS IN FLIGHT: 0` while
  `unattributed_probe` reports `True` -- `wait_for_slot` must NOT report
  free, and times out with `EXIT_TIMEOUT` (a real condition was
  measured, never `EXIT_SLOT_FREE`).
- `test_no_land_at_all_still_returns_free_promptly`: no land in flight
  and `unattributed_probe` reports `False` -- the slot is reported free
  immediately, proving the fix does not degenerate into "never reports
  free".
- The three `TestProbeUnattributedLandProcess` tests are the same two
  directions at the lower `probe_unattributed_land_process` layer, plus
  the empty-rows case.

`fleet_status.py`'s own `LANDS IN FLIGHT` line is left unchanged (out of
this ticket's declared scope, `scripts/wait_for_land_slot.py` only) --
the ticket's own "consider also" note about `fleet_status.py` adopting
the broader definition is left for the coordinator to weigh separately,
since changing it would affect every OTHER `land_invocations()` consumer
(the per-invocation pid/cpu reporting), not just this wait primitive.

Filed: T-2817 (docs-kind follow-up: add the real
docs/guides/coordinator-scripts.md anchor/section for the new probe once
T-2755's lease on that file clears; the two frob:waive COV001/AFFECT001
comments in scripts/wait_for_land_slot.py name it directly).

Gates: `frob check --ticket T-2807 --only gates-fast` clean of in-scope
findings after fixing two `frob:tests` target-path typos (pointed at
test_coordinator_scripts.py before the test file was moved to its own
file to avoid a lease conflict) and waiving COV001/AFFECT001 with the
doc-lease reason above. The one remaining scope-adjacent note (SCOPE001
on tickets/T-2817/ticket.md, the auto-committed ticket-filing
commit) is the standard residue-ticket-filing shape, not a change this
ticket's own diff makes. All other errors surfaced are pre-existing
repo-wide baseline (ledger backlog/TICK, unrelated DRIFT/DOC/TEST
findings in other modules, claude-config-drift) -- verified unrelated by
symbol name, none touch scripts/wait_for_land_slot.py or the new test
file. `pytest tests/unit/test_wait_for_land_slot_unattributed.py
tests/unit/test_coordinator_scripts.py` (12 collected filtered to the
relevant classes, 0 failed); the one pre-existing unrelated failure in
that file (TestInProgressTicketScopeLeasesLiveGit, a live-git-worktree
scope-lease test) reproduces identically on main's own root with no
changes applied.
