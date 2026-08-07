## Done report

Two of the four regressions were already fixed by another concurrent land
before I started this ticket:
- `tests/unit/test_ticket_runner_gate_findings.py:41-42`'s ty
  `invalid-parameter-default` pair: `errors`/`warnings` are now typed
  `Sequence[tuple[str, str, str]]` (not `list[...]`), which a `()`
  default satisfies. Confirmed clean: `uv run ty check tests/unit/
  test_ticket_runner_gate_findings.py` -> "All checks passed!", and
  `git show main:...` already has this shape -- no action needed here.

The two COV003s were real and are fixed by this ticket:
- T-1679 renamed `tests/unit/test_ticket_store.py::TestWriteTicket`'s
  `test_content_loss_warns_loudly_by_default` ->
  `test_non_strict_opt_out_warns_loudly_instead_of_refusing` and
  `test_strict_no_content_loss_refuses` ->
  `test_content_loss_refuses_by_default` (the T-1679 default-flip made
  the old names describe the WRONG behavior: the first no longer
  describes "loudly by default", the second no longer needs "strict" to
  be named since strict is now the default). T-1637 (DONE) had bound its
  own evidence to the old names, so its COV003 broke.
- Re-bound via `frob ticket evidence T-1637 --replace <old> <new>` for
  both. Root cause of why this survived my own T-1679 gate checks but
  never reached main: `frob ticket land`'s squash-apply only carries the
  LANDING ticket's own `tickets.md` block forward, not incidental edits
  to OTHER tickets' blocks made in the same worktree along the way -- the
  T-1637 rebind was a real, correct change I made mid-T-1679, but it was
  never itself the subject of a land, so it silently never reached main.
  This ticket's own land is what actually carries it.
- Confirmed the rebound ids genuinely exercise the SAME behavior T-1637
  claimed, not just that they resolve: `test_non_strict_opt_out_warns_
  loudly_instead_of_refusing` is the renamed continuation of the exact
  "write discards content, `strict_no_content_loss=False`, logs a loud
  warning and proceeds" scenario the old `test_content_loss_warns_
  loudly_by_default` tested (same body, only the default-vs-explicit
  framing changed by T-1679's flip). `test_content_loss_refuses_by_
  default` is the renamed continuation of the exact "write discards
  content, refuses" scenario the old `test_strict_no_content_loss_
  refuses` tested (same assertion shape, now the DEFAULT path instead of
  an explicit `strict_no_content_loss=True` opt-in). Ran both directly:
  `uv run pytest tests/unit/test_ticket_store.py::TestWriteTicket::test_
  non_strict_opt_out_warns_loudly_instead_of_refusing tests/unit/test_
  ticket_store.py::TestWriteTicket::test_content_loss_refuses_by_default
  -q` -> 2 passed.

Verification per the ticket's own closing bar (a `--ticket`-scoped zero
does not close this): ran an UNSCOPED `uv run frob check --budget 500`
against the current tree (T-1637's rebind plus the already-fixed ty
annotation). Top-line result: `3 errors, 580 warnings` -- exactly the
`## Errors` DOC009 (docs/audits/docs-completeness-2026-08-06.md) +
ARCH001 (`_evidence.py::_done_transition_structural_guard`) plus the
separate `ty` tool's 1 diagnostic (`test_ticket_work_and_land_finish.py`
`unresolved-attribute`) -- the exact 3 pre-existing errors T-1685 tracks,
confirmed by name against the ticket's own explicit list. No new errors.

frob:waive BUG002 reason="this ticket's own fix is a tickets.md evidence rebind (T-1637's citation onto its renamed test names) plus confirming an already-fixed ty annotation elsewhere -- not a runtime code-behavior change of its own. The bound evidence tests exercise T-1679's write_ticket behavior (which they already did before this ticket existed) to confirm the rebind resolves to tests that genuinely test the claimed behavior, not to demonstrate a NEW fix this ticket's own diff makes. There is no code path this ticket changes that a repro-at-parent test could meaningfully fail against."

### Changed
```
 tickets.md | 280 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++-
 1 file changed, 277 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/unit/test_ticket_store.py::TestWriteTicket::test_non_strict_opt_out_warns_loudly_instead_of_refusing` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_store.py::TestWriteTicket::test_content_loss_refuses_by_default` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 3 error(s), 191 warning(s), 716 waived
- error-findings: ARCH001@src/frob/tickets/_evidence.py, DOC009@docs/audits/docs-completeness-2026-08-06.md, unresolved-attribute@tests/test_ticket_work_and_land_finish.py
