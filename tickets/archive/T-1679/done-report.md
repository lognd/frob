## Done report

T-1637's content-loss guard (`_check_no_content_loss` in `write_ticket`)
shipped `strict_no_content_loss=False` as the DEFAULT: a write that would
replace an existing ticket's evidence list and/or Done report with an
empty one only LOGGED a loud warning and proceeded, never refused. That
made the guard a detector, not a guard -- the T-1636 incident it exists
to prevent (12 evidence ids + a 12KB Done report discarded, recoverable
only via git archaeology) would still happen today under the old default,
just with a log line attached, since nothing in the real `frob ticket`/
`land` call chain ever opted into `strict_no_content_loss=True`.

Fix:
1. `write_ticket`'s default flipped to `strict_no_content_loss=True`
   (refuse). `strict_no_content_loss=False` still exists as an explicit,
   disclosed opt-out for a caller with a specific reason to want the old
   warn-and-proceed behavior.
2. Added `_write_ticket_unchecked` (private, `frob.tickets._store`): the
   explicit, self-documenting escape hatch for a genuine "construct a
   deliberately poorer ticket snapshot on purpose" caller -- skips the
   content-loss check ENTIRELY, no warning at all, and says so plainly at
   the call site instead of `write_ticket` itself needing a weaker
   default to accommodate it.
3. Moved every test fixture that relied on the old lax default onto
   `_write_ticket_unchecked`: the `splice_ledger` merge-preference
   fixtures in `tests/test_ticket_land.py`
   (`TestSpliceLedgerRicherStatePreference`,
   `TestSpliceLedgerPrefersEvidenceRichSideOnRankTie`) and the
   `TICK005` land-regression-simulation fixtures
   (`TestTick005LandRegressions`). Six call sites total, matching the
   ticket's own "six pre-existing splice_ledger test fixtures" count.
4. Audited every remaining production `write_ticket` call site
   (`frob.tickets._setters`/`_evidence`/`_scope`/`_accept`/`_reporting`/
   `_reporting_attachments`/`_new_renumber`/`__init__`/`_land_verify`,
   `frob.app.ticket_runner._lifecycle`) -- none passes
   `strict_no_content_loss` explicitly, so every one of them now gets the
   strict-by-default refusal. Confirmed by running the FULL
   `write_ticket`-touching test surface (325+ tests across
   `tests/unit/test_ticket_store.py`, `tests/test_ticket_land.py`, plus a
   broader sweep of every other file importing `write_ticket`) after the
   flip: no production caller legitimately needs to empty both fields at
   once -- if one did, its own test would have broken the same way the
   six fixtures did.

Also rebound T-1637's own recorded evidence (`frob ticket evidence
--replace`) onto the renamed test methods
(`test_content_loss_warns_loudly_by_default` ->
`test_non_strict_opt_out_warns_loudly_instead_of_refusing`,
`test_strict_no_content_loss_refuses` ->
`test_content_loss_refuses_by_default`) so its own COV003 evidence
resolution stays intact after the rename.

Filed T-1711 (renumbers at land) as the WIRE002-required
follow-up ticket for `_write_ticket_unchecked`'s WIRE001 waiver (it lives
in `src/`, so the test-tree `permanent="true"` exemption does not apply)
-- investigates whether the primitive could instead live in a `tests/`-
tree helper module.

### Changed
```
 docs/modules/tickets.md         |  51 +++++---
 src/frob/tickets/_models.py     |   7 +-
 src/frob/tickets/_store.py      |  62 ++++++++--
 tests/test_ticket_land.py       |  14 +--
 tests/unit/test_ticket_store.py | 102 +++++++++++-----
 tickets.md                      | 254 +++++++++++++++++++++++++++++++++++++++-
 6 files changed, 416 insertions(+), 74 deletions(-)
```

### Evidence
- `tests/unit/test_ticket_store.py::TestWriteTicket::test_content_loss_refuses_by_default` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_store.py::TestWriteTicket::test_non_strict_opt_out_warns_loudly_instead_of_refusing` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_store.py::TestWriteTicketUnchecked::test_skips_the_content_loss_guard_entirely` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestSpliceLedgerRicherStatePreference::test_report_side_still_wins_when_it_also_outranks_the_reportless_side` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestTick005LandRegressions::test_detects_terminal_ticket_regressed_to_non_terminal` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 7 error(s), 666 warning(s), 716 waived
- error-findings: AFFECT001@src/frob/tickets/_store.py, ARCH001@src/frob/tickets/_evidence.py, DOC009@docs/audits/docs-completeness-2026-08-06.md, INV006@src/frob/gates/_markdown_scan.py, PII012@tests/unit/gates/test_markdown_scan.py, invalid-parameter-default@tests/unit/test_ticket_runner_gate_findings.py, unresolved-attribute@tests/test_ticket_work_and_land_finish.py
