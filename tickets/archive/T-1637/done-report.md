## Done report

DESIGN PIVOT mid-ticket (coordinator directive, same message as T-1622's):
kept everything from the original T-1637 brief -- especially deliverable
(c), refusing/warning on discarding a Done-report/evidence-carrying
block -- and confirmed `frob ticket renumber` already existed as the
correct atomic rename primitive.

Deliverable 1 -- first-class promotion path: added `frob ticket promote
<draft-id>` (`frob.app.ticket_runner._query._promote`), a thin CLI
wrapper over the EXISTING `finalize_draft` (`frob.tickets._draft_
finalize`), which itself calls `renumber_one` -- so promotion needed
almost no new logic, exactly as the coordinator anticipated. It allocates
the draft's next real id against the current merged (active+archive)
view and rewrites the ledger block plus every code reference in one
atomic rename. Because it renames the SAME `Ticket` object rather than
reconstructing a fresh one, evidence/Done report/scope/state/acceptance
all move onto the new id automatically -- proven end to end by
`tests/system/test_cli_ticket_promote.py::TestPromoteCLI::
test_promotes_a_draft_carrying_evidence_and_done_report` (files a draft
via the real CLI, gives it evidence + a Done report via `write_ticket`,
promotes it via `frob ticket promote`, asserts both survived intact on
the promoted ticket) and `test_promoting_an_already_final_id_is_a_no_op`
(idempotent no-op for a non-draft id, matching `finalize_draft`'s own
contract). CLI wiring: `src/frob/_cli_parsers/_ticket/_progress.py`
(`_add_ticket_promote_parser`), `src/frob/app/ticket_runner/__init__.py`
(dispatch table + import + `__all__`), `src/frob/app/ticket_runner/
_query.py` (`_promote`). Manual smoke test also run (a real `git
worktree`, `frob ticket new` off-branch, `frob ticket promote`) --
confirmed the draft's block on disk carries the real id with zero
`T-draft-` strings remaining.

Deliverable 2 -- document `renumber`/`promote` as the refile path:
added a paragraph to `docs/guides/agent-playbook.md` section 0 item 8
(the existing "every residue/follow-up you file is a draft" guidance)
naming the lossy hand-recipe explicitly, pointing at `frob ticket
promote` for the pre-land case and `frob ticket renumber <old> <new>`
for the case both ids are already known. Also documented `promote` and
the content-loss guard as two new subsections in `docs/modules/
tickets.md`, and a shorter cross-reference note in `docs/design/
ledger-v2.md`'s lock-model section (needed to satisfy AFFECT001, since
`write_ticket`'s affects()-closure names that doc).

Deliverable 3 (the one that generalizes) -- content-loss guard on
`write_ticket`: `_check_no_content_loss` (`frob.tickets._store`) compares
an incoming write against the on-disk ticket for that id; if the on-disk
version carries non-empty evidence or a `## Done report` heading and the
incoming write has NEITHER, the write is flagged. Default
(`strict_no_content_loss=False`, every EXISTING call site unchanged) is a
LOUD warning naming exactly what would be discarded, not a refusal --
proven this was the right default the hard way: a first pass made this a
hard refuse by default and it broke 6 pre-existing tests in
`tests/test_ticket_land.py` (`TestSpliceLedgerRicherStatePreference`,
`TestSpliceLedgerPrefersEvidenceRichSideOnRankTie`,
`TestTick005LandRegressions`) whose fixtures legitimately construct a
"poorer" ticket snapshot via `write_ticket` directly to simulate a
stale/regressed ledger side for `splice_ledger`'s own merge-preference
tests. `strict_no_content_loss=True` is available for a caller that wants
the harder guarantee (an interactive command a human drives directly);
nothing in this ticket's own scope currently sets it (a future `frob
ticket promote --strict`-style flag, or an interactive confirmation
prompt, is the natural next step but was not asked for and was not
added). This is the sibling of the existing `_post_splice_integrity_
check` (T-0764/T-1536) one level down: that guard protects an id from
vanishing from the ledger outright; this one protects the recorded WORK
on a surviving id from silently vanishing -- the exact T-1636 shape.
Tests: `TestWriteTicket::test_content_loss_warns_loudly_by_default`
(warns, does not block, verified via `caplog`), `test_strict_no_content_
loss_refuses` (opts in, blocks, verified the on-disk content is
unchanged after refusal), `test_keeping_evidence_or_done_report_is_never_
refused` (only clearing BOTH trips it -- clearing just one is fine),
`test_first_write_for_a_new_id_is_never_refused` (no prior content, no
guard).

Corrected a directive-placement mistake mid-ticket: the two new helper
functions were initially placed directly above `write_ticket`'s own
frob:doc/frob:tests directive block, so COV005 correctly flagged the
directives as having silently ridden onto the new private helpers
instead of staying bound to `write_ticket`. Moved both helpers to after
`write_ticket`'s body (Python resolves the forward reference at call
time, so no functional change) -- `frob check --only coverage --ticket
T-1637` went from 60 errors to 0.

Filed: none. No out-of-scope gap found.

Evidence: 6 ids recorded (`frob ticket evidence T-1637 ...`), all
collected and passing:
- tests/unit/test_ticket_store.py::TestWriteTicket::test_content_loss_warns_loudly_by_default
- tests/unit/test_ticket_store.py::TestWriteTicket::test_strict_no_content_loss_refuses
- tests/unit/test_ticket_store.py::TestWriteTicket::test_keeping_evidence_or_done_report_is_never_refused
- tests/unit/test_ticket_store.py::TestWriteTicket::test_first_write_for_a_new_id_is_never_refused
- tests/system/test_cli_ticket_promote.py::TestPromoteCLI::test_promotes_a_draft_carrying_evidence_and_done_report
- tests/system/test_cli_ticket_promote.py::TestPromoteCLI::test_promoting_an_already_final_id_is_a_no_op

Gates: `frob check --only coverage --ticket T-1637` clean (0 errors, 1
warning, 171 waived). `frob check --only affect_drift --only prework
--ticket T-1637` clean (0 errors). Full regression pass on touched test
files: `tests/unit/test_ticket_store.py`, `tests/system/
test_cli_ticket_promote.py`, `tests/test_ticket_land.py` (326 collected,
0 failed).

### Changed
```
 docs/design/ledger-v2.md                   |  15 ++++
 docs/guides/agent-playbook.md              |  17 ++++
 docs/modules/tickets.md                    |  79 +++++++++++++++++
 src/frob/_cli_parsers/_ticket/_progress.py |  21 +++++
 src/frob/app/ticket_runner/__init__.py     |   4 +
 src/frob/app/ticket_runner/_query.py       |  43 ++++++++++
 src/frob/tickets/_models.py                |  18 ++++
 src/frob/tickets/_store.py                 |  97 ++++++++++++++++++++-
 tests/system/test_cli_ticket_promote.py    | 130 ++++++++++++++++++++++++++++
 tests/test_ticket_land.py                  |  88 +++++++++++++++++++
 tests/unit/test_ticket_store.py            |  94 +++++++++++++++++++++
 tickets.md                                 | 131 ++++++++++++++++++++++++++++-
 12 files changed, 733 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/unit/test_ticket_store.py::TestWriteTicket::test_content_loss_warns_loudly_by_default` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_store.py::TestWriteTicket::test_strict_no_content_loss_refuses` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_store.py::TestWriteTicket::test_keeping_evidence_or_done_report_is_never_refused` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_store.py::TestWriteTicket::test_first_write_for_a_new_id_is_never_refused` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_ticket_promote.py::TestPromoteCLI::test_promotes_a_draft_carrying_evidence_and_done_report` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_ticket_promote.py::TestPromoteCLI::test_promoting_an_already_final_id_is_a_no_op` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 0 error(s), 4942 warning(s), 713 waived
- error-findings: none (measured, zero errors)
