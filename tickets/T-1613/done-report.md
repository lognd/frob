## Done report

Added a `runs_last: bool` marker (T-1613) to `Ticket`/`TicketSpec` that keeps
a ticket structurally undoable while any other ticket is open -- not merely
advisory (the scope-ack/TICK009 failure mode).

Definition chosen for "any other ticket open": every OTHER ticket, excluding
fellow runs-last tickets, whose state is non-terminal
(queued/planned/in-progress/blocked -- the same `_OPEN_STATES` set
`blocked_by` already uses). This was the strict choice over "only
in-progress with a live lease": a queued ticket someone starts a minute
later is the identical hazard, just deferred, so gating on in-progress alone
would leave the exact dispatch-into-the-window gap the marker exists to
close. Fellow runs-last tickets are excluded from the count so two or more
can coexist and order among themselves via ordinary `blocked_by`, per the
ticket's own requirement.

Enforcement, two structural points (never a warning-only nudge):
- `doable` (`frob.tickets._doable._doable_candidates`, new
  `_other_open_tickets` helper): a runs-last candidate never surfaces while
  the check above is non-empty.
- `start` (`frob.tickets._evidence._transition_guard`'s IN_PROGRESS branch,
  new `_runs_last_start_blockers`): the transition refuses with a new
  `TicketError.RunsLastBlocked`, and the log line names every remaining
  open ticket id.

Filing-invalidation warning (the requirement that makes this real rather
than cosmetic): `frob.tickets._new_renumber.new_ticket` now calls
`_warn_if_runs_last_ticket_in_progress` before every fresh ORDINARY
(non-runs-last) ticket is filed -- logs a loud WARNING naming every
IN_PROGRESS runs-last ticket, does not block filing.

CLI surface: `frob ticket runs-last <id> <on|off>` (new `set_runs_last`
setter mirroring `set_tier`), wired through the full parser tree
(`_cli_parsers/_ticket/_metadata.py` + `__init__.py`), `AppConfig`
(`app/config.py` + the `_config_external.py` string-field allowlist --
confirmed by direct repro that omitting the allowlist entry means argparse
parses the value but `AppConfig` never receives it), and the dispatch table
(`app/ticket_runner/_mutate.py::_runs_last` + `app/ticket_runner/__init__.py`).
Did not wire a `--runs-last` flag onto `frob ticket new` itself (kept the
surface to the minimum needed to verify the mechanism end to end) --
setting it via `runs-last <id> on` immediately after filing is the current
path; a `new --runs-last` convenience flag is a natural, small follow-up if
wanted.

Verified end-to-end by hand in a scratch repo (not just unit tests): filed
a runs-last ticket, filed an ordinary ticket, confirmed `doable`/`start`
both refuse the runs-last ticket, dropped the ordinary ticket, confirmed
`doable`/`start` succeed once it was the only open ticket, started the
runs-last ticket, filed a fresh ordinary ticket, confirmed the WARNING
fires naming the running ticket id, and confirmed two runs-last tickets
coexist and both surface in `doable`.

Scope grew substantially past the narrowed dispatch scope (which covered
only `_models.py`/`_store.py`/query-side files) because the actual
enforcement points live in `_doable.py` (doable filtering) and
`_evidence.py` (start-time transition guard), neither of which were in the
original grant; extended with `--reason` file by file as each dependency
surfaced (`_doable.py`, `_evidence.py`, `_new_renumber.py`, `_setters.py`,
`_cli_parsers/_ticket/_metadata.py` and its `__init__.py`,
`app/ticket_runner/_mutate.py`, `app/_config_external.py`,
`docs/modules/tickets.md`, `design/frob.strata`, and this ticket's own v2
ledger file `tickets/T-1613/ticket.md`, which SCOPE001 flagged as outside
scope despite `LEDGER_PATH`'s always-implicit rule only covering the
legacy single-file `tickets.md` path, not this checkout's v2 per-ticket
layout). Landed as one ticket per the "propose a split only if it turns
out larger" instruction -- the mechanism is cohesive (one field, two
enforcement points, one warning, one CLI verb) and none of it works
half-landed.

`frob check --only prework --only scope --only sys --ticket T-1613` is
clean (PRE001/SCOPE001/SELFAUDIT001 all resolved). `frob fmt --check`
found the repo's pre-existing 51-file litmus/`.strata` reformatting debt,
unrelated to this ticket; the one file this ticket actually touched that
needed reformatting (`_setters.py`) is now clean.

### Changed
```
 tickets/T-1613/done-report.md |  94 ++++++++++++++++++++++++++++
 tickets/T-1613/ticket.md      | 139 +++++++++++++++++++++++++++++++++++++++++-
 2 files changed, 232 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_tickets_organization.py::TestRunsLast::test_set_runs_last_updates_field` (pytest node id, verified passing when recorded)
- `tests/test_tickets_organization.py::TestRunsLast::test_doable_excludes_runs_last_while_other_ticket_open` (pytest node id, verified passing when recorded)
- `tests/test_tickets_organization.py::TestRunsLast::test_doable_includes_runs_last_once_all_other_tickets_terminal` (pytest node id, verified passing when recorded)
- `tests/test_tickets_organization.py::TestRunsLast::test_start_refuses_runs_last_while_other_ticket_open` (pytest node id, verified passing when recorded)
- `tests/test_tickets_organization.py::TestRunsLast::test_multiple_runs_last_tickets_do_not_block_each_other` (pytest node id, verified passing when recorded)
- `tests/test_tickets_organization.py::TestRunsLast::test_filing_new_ticket_while_runs_last_in_progress_warns` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 0 error(s), 1176 warning(s), 723 waived
- error-findings: none (measured, zero errors)
