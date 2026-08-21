## Done report

Verified independently, no work needed:

- `tests/unit/test_land_finish_guard.py:69-72`'s WIRE001 waiver on
  `_add_worktree` cites `follow_up="T-1778"` (confirmed by direct read of
  the file, not by trusting the ticket body's prior claim).
- `tickets/T-1778/ticket.md` carries `anchor: true`,
  `anchor_reason: permanent WIRE001 waiver home for tests/unit/
  test_land_finish_guard.py:_add_worktree`, and `state: queued` --
  non-terminal, exactly as an anchor ticket must stay per T-1856 (a
  citation's own target ticket must never reach a terminal state, or the
  waiver it anchors loses its live follow_up target).
- The citation is not dangling: its target exists, is correctly typed as
  an anchor, and sits in a valid non-terminal state. Nothing to re-home.

This ticket's own Failure log (2026-08-08 attempt 1) already recorded
that its re-point work landed to main and that closing it to DONE is
categorically wrong for an anchor ticket -- confirmed still true. T-1868/
T-1874 (`_skip_close_for_anchor_no_close_requested`, landed since that
failure log entry, and which names this exact ticket in its own
docstring as the incident that motivated it) now gives `frob ticket land`
a legal way to publish this ticket's record as-is without forcing a
`queued -> done` transition. Landing this Done report exercises that path
rather than repeating the 2026-08-08 fail-attempt workaround.

Changed: none -- no code or doc edit required; scope file
(`tests/unit/test_land_finish_guard.py`) already correct.

Evidence: tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
(pre-existing, unchanged).

Filed: none.

Gates: no new findings possible from a no-op change; anchor/state
invariants verified by direct read, not gate output.
