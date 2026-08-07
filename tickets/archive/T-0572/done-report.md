## Done report

Implemented T-0572 acceptance-evidence binding: close now verifies the
acceptance MAPPING, not just evidence existence.

CLI surface:
- `frob ticket evidence <id> <node-id>... --accepts N [N ...]` and
  `frob ticket close <id> --evidence <node-id>... --accepts N [N ...]`
  bind the given evidence id(s) onto each named (0-based)
  ticket.acceptance index, in the same atomic write as the evidence-list
  append (add_evidence(..., accepts=...)).
- `frob ticket show <id>` now renders an `acceptance:` block listing each
  criterion's index, bound/UNBOUND status, and text, so an operator can
  find the index to bind without --json.

Model: `Ticket.acceptance`/`TicketSpec.acceptance` changed from
`tuple[str, ...]` to `tuple[AcceptanceCriterion, ...]`
(`{text: str, evidence: tuple[str, ...]}`). A before-validator
(`_coerce_acceptance`) accepts legacy plain-string items from
pre-T-0572 ledgers and wraps them as unbound criteria, so every
existing ticket still loads unchanged.

Close semantics: `_done_transition_guard` (the same gate both the
`close` and land-time paths route through) now also calls
`unbound_acceptance(ticket)` and refuses the DONE transition
(`Err(AcceptanceUnbound)`) naming the unbound criterion text(s) in the
WARNING log line if any acceptance item has no evidence id that both
the criterion lists AND still resolves against `ticket.evidence`. A
ticket with an empty `acceptance` list is completely unaffected
(backward compat) -- verified directly by
`test_ticket_with_no_acceptance_list_closes_as_before`, and the refusal
naming the criterion is verified directly by
`test_unbound_acceptance_criterion_refuses_close`'s caplog assertion
(added on reviewer request -- the test previously only checked the
exit code, not that the criterion TEXT was actually surfaced).

Gate/test numbers actually observed (corrected after a reviewer
rejection caught false numbers in an earlier draft of this report --
see below):
- `uv run pytest tests/test_tickets_acceptance.py tests/test_tickets.py
  tests/test_tickets_evidence_cli.py tests/test_tickets_brief.py -p
  no:cacheprovider` -> **142 passed**, 0 failed (11 + 102 + 13 + 16 across
  the four files, in tests/test_tickets_acceptance.py/test_tickets.py/
  test_tickets_evidence_cli.py/test_tickets_brief.py order; re-confirmed after every subsequent change in this
  ticket, most recently after adding the caplog assertion).
- `uv run frob check --ticket T-0572` -> gate-summary **FAIL, 28
  errors**, 410 warnings, 200 waived (last observed run, right before
  this final commit). All 28 are COV003 stale-evidence findings on
  OTHER tickets (14 on T-0587, 10 on T-0617, 3 on T-0630, 1 on T-0724) --
  **0 errors attributable to T-0572** (confirmed by filtering the
  `--json` output for `file` containing "T-0572": empty every time this
  was re-checked). These tickets' evidence references tests this
  worktree's merge point predates on a fast-moving shared `main` that
  kept landing new tickets throughout this session (the count moved
  27 -> 28 between two checks a few minutes apart, purely from that);
  not caused by this ticket, self-resolves once this worktree next
  merges current main. ruff-check/ruff-format/ty all show `pass`/
  "no issues" with zero errors throughout.
  CORRECTION (reviewer-caught): an earlier draft of this report
  incorrectly stated "gate-summary 0 errors" and "145 passed" -- neither
  number was ever actually observed: "145" came from miscounting
  separate per-file runs, and "0 errors" came from not reading past the
  gate-summary FAIL line to see it was reporting 27 (now 28) real COV003
  findings, just none attributable to this ticket. Every number in this
  report is now a freshly re-run, actually-observed figure, not carried
  forward from that draft.

Legacy-acceptance-block migration (T-0572, done proactively on
reviewer request, not left to ambush a future land): the schema change
above meant the NEXT whole-ledger write (any land splice, renumber, or
write_all) would reformat every pre-existing plain-string acceptance
block the first time it touched the ledger. Migrated deliberately now,
in its own commit
(`chore(tickets): migrate legacy acceptance blocks to {text, evidence}
form (T-0572)`): loaded both `tickets.md` and `tickets-archive.md` into
id -> Ticket maps, wrote them back out through the same
`write_all`/`write_archive` -> `_render_ledger` path any splice already
uses, reloaded, and asserted frozen-pydantic `Ticket` equality
(every field, including id/state/evidence/acceptance) for all
tickets -- **208 active + 516 archive tickets checked, zero
mismatches**. Migrated **113 active + 44 archive tickets with
non-empty acceptance (227 criteria, 157 legacy blocks total)**. Ticket
id sets and file ordering are unchanged; the diff is confined to
acceptance-block formatting (measured 911 insertions/658 deletions across both
files (git diff --stat), consistent with 157 blocks reformatting from a single YAML
list-of-strings into a list-of-mappings).

Mid-ticket, main advanced past this worktree's original merge point
multiple times (a live, shared, fast-moving ledger with concurrent
agents landing work) -- landed T-0728 ARCH1xx work, then T-0729/T-0617/
T-0630 ARCH1xx OCP work, etc. Re-ran `git merge main` once (a
legitimate code catch-up per the playbook, not a late ledger-only
sync) early on; caught the ticket-merge-driver's whole-ledger re-render
(triggered by this ticket's own schema change) picking a stale copy of
another ticket's state (T-0630 'done' -> 'queued') via the
deletion-filter/ledger-diff review this playbook mandates before
finishing. Fixed via the documented restore + replay recipe (`git
checkout main -- tickets.md`, then replay ONLY T-0572's own
scope/start/evidence/done-report CLI calls) -- redone twice more as
main kept advancing during the fix itself. Final `git diff main --
tickets.md` touches only T-0572's own section (one `state:` line, its
own scope/evidence/Done-report fields) plus the deliberate migration
commit's acceptance-block reformatting (not a state change on any
other ticket). `git diff main --diff-filter=D --stat` was verified
empty at each merge point actually used; main's continued forward
motion after that point is a live-ref staleness artifact, not evidence
of anything this ticket deleted.

Scope was extended several times beyond the initial filing (each via
`frob ticket scope --add --reason`, not silently): `src/frob/__main__.py`
(CLI arg wiring, the CLI_WIRING_FILES pattern this repo already
documents for any FEATURE ticket adding flags), `pyproject.toml` +
`.frob-release.json` + `uv.lock` (REL001's mandatory version-bump
companion, 0.89.0 -> 0.90.0), `tickets-archive.md` (the deliberate
migration above).

Not done / left for a follow-up ticket if wanted: `--evidence-cmd`
(the non-pytest, docs-kind evidence channel) does not currently thread
through `--accepts` -- only the pytest-node-id evidence path binds
acceptance criteria. No new ticket was filed for this since it is a
narrow, docs-kind-only gap noted here rather than a defect found
outside this ticket's scope.

### Changed
```
 docs/modules/tickets.md          |  27 +++-
 src/frob/__main__.py             |  23 +++
 src/frob/app/config.py           |   6 +
 src/frob/app/ticket_runner.py    |  58 +++++++-
 src/frob/tickets/__init__.py     |  76 ++++++++--
 src/frob/tickets/_brief.py       |   8 +-
 src/frob/tickets/_models.py      |  90 +++++++++++-
 tests/test_tickets.py            |   9 +-
 tests/test_tickets_acceptance.py | 304 +++++++++++++++++++++++++++++++++++++++
 tests/test_tickets_brief.py      |   5 +-
 10 files changed, 584 insertions(+), 22 deletions(-)
```

### Evidence
(no evidence recorded)
