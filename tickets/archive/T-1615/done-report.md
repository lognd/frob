## Done report

Root cause: `frob ticket block` (and, per the audit below, nine other
verbs) wrote the ledger and left it dirty. T-1130/T-1178 gave `new`/
`drop`/`fail`/`start`/`close`/`evidence`/`done-report`/`requeue` their
own per-verb `commit_ticket_ledger_change` call, but every OTHER
ledger-writing verb added since was never wired the same way -- the
"verb number twelve" gap.

Fix (deliberately NOT one more per-verb copy-paste): `frob.app.
ticket_runner._auto_commit_ledger_after_dispatch` wraps the SINGLE
dispatch call site in `run()`, so a verb added to `_ticket_dispatch_
table()` later is covered automatically. `archive` (a whole-ledger
write, not scoped to one `cfg.ticket_id`) gets its own explicit call
site instead -- `commit_full_ledger_change`, `commit_ticket_ledger_
change`'s twin keyed on the whole active+archive ledger surface.
`commit_ticket_ledger_change` itself now warns loudly (naming ticket,
root, and the exact recovery command) whenever `--no-commit` leaves the
ledger dirty, for every verb that reaches it.

## Audit table (every ledger-writing verb, enumerated from the real
dispatch table by `tests/test_ticket_leases.py::
TestLedgerAutoCommitEnumeratedOverDispatchTable`, not hand-listed --
`test_dispatch_table_verbs_are_all_accounted_for` fails the instant a
future verb is added without being triaged into one of its buckets)

| verb | writes ledger? | commits? | mechanism |
|---|---|---|---|
| new/drop/fail/start/close/evidence(+--replace)/done-report/requeue | yes | yes (pre-existing) | T-1130/T-1178 own call sites |
| block | yes | **yes (T-1615, was the trigger)** | uniform wrapper |
| scope/scope-ack | yes | **yes (T-1615)** | uniform wrapper |
| priority/kind/component/label/tier | yes | **yes (T-1615)** | uniform wrapper |
| accept (append/--amend/--remove) | yes | **yes (T-1615)** | uniform wrapper |
| attach | yes | **yes (T-1615)** | uniform wrapper |
| sprint assign | yes | **yes (T-1615)** | uniform wrapper |
| review | yes | **yes (T-1615)** | uniform wrapper |
| archive | yes, whole ledger | **yes (T-1615)** | `commit_full_ledger_change`, own call site |
| migrate | yes, whole ledger | deliberately no | rewrites the storage backend (v1->v2) itself |
| renumber (both forms) / promote | yes, whole tree | deliberately no | rewrites frob:ticket/frob:tests directives across every tracked file, not just the ledger -- a ledger-only commit would split one atomic rename in two |
| land / merge-driver | yes, whole tree | yes, via its OWN multi-file commit sequence | never through this mechanism |
| sweep-async | no (files a new ticket, which already commits) | n/a | T-1699's own territory |
| reverify | no (re-verifies an already-done ticket, never transitions) | n/a | -- |
| list/show/doable/board/epic/brief/flow/sprint show/plan/work/sweep/reconcile | no | n/a | read-only or state-check-only |

No `unblock` verb exists in the dispatch table.

Full table + rationale also recorded in docs/modules/tickets.md under
"Every ledger-writing verb auto-commits uniformly (T-1615)".

Test shape (T-1615's own requirement): `test_verb_leaves_repo_clean`
parametrizes over every entry in a per-verb invocation map, asserting
the repo is CLEAN after running it against a real git-backed fixture;
`test_dispatch_table_verbs_are_all_accounted_for` is the completeness
guard.

Incidental fixes found auditing: `ticket_no_commit`'s CLI dest was
entirely missing from `src/frob/app/_config_external.py`'s bool-flags
allowlist (WIRE001) -- pre-existing for close/evidence/done-report/
requeue too, not something my new wiring introduced, but caught here
since my new `--no-commit` flags on block/scope/etc. are the first ones
this gate's diff-driven check happened to flag it against. Added once,
fixes it for every verb using that dest.

Evidence: tests/test_ticket_leases.py::TestCommitTicketLedgerChange's warn tests, TestCommitFullLedgerChange's 4 tests (dirty-commit, no-op, no-commit-warns, real archive-CLI-cycle), TestLedgerAutoCommitEnumeratedOverDispatchTable's completeness guard + parametrized per-verb clean-repo assertion (10 verbs: block/scope/priority/kind/component/label/accept/tier/attach/requeue).

Filed: none new for this ticket's own scope (checked `frob ticket list`
first). T-1704 (the earlier, over-broad-scoped attempt at this same
ticket) was already dropped as a duplicate before this dispatch.

Gates: `frob check --ticket T-1615` gate-summary 0 errors (after
merging main to its true current tip -- this worktree's branch had
fallen behind after each of T-1677/T-1672/T-1587's own lands, each time
producing phantom findings against already-landed code, resolved by
merging, never by touching that code; also hit and worked around the
T-0731 land-owned-files pre-commit hook when merging in a main that had
moved a version bump -- see the "sync land-owned files to main's tip"
commit, `FROB_LAND_INTERNAL=1` used narrowly for a merge-only follow-up
with zero content of my own, matching the hook's own documented
escape-hatch intent). ruff-check/ty both clean on every touched file.
`frob test --base main` exit=0 (152+ python tests, 0 failed) at the
final tree state.

### Changed
```
 design/frob.strata                         |   2 +-
 docs/guides/agentic-workflow.md            |   2 +
 docs/modules/tickets.md                    |  75 ++++++++
 src/frob/_cli_parsers/_ticket/_closeout.py |  27 +++
 src/frob/_cli_parsers/_ticket/_metadata.py |  25 +++
 src/frob/app/_config_external.py           |   2 +
 src/frob/app/ticket_runner/__init__.py     |  98 ++++++++++-
 src/frob/app/ticket_runner/_archive.py     |  22 ++-
 src/frob/tickets/_leases.py                | 239 ++++++++++++++++++++------
 tests/test_ticket_leases.py                | 263 +++++++++++++++++++++++++++++
 tickets.md                                 | 105 +++++++++++-
 11 files changed, 798 insertions(+), 62 deletions(-)
```

### Evidence
- `tests/test_ticket_leases.py::TestCommitTicketLedgerChange::test_no_commit_flag_warns_when_dirty` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestCommitTicketLedgerChange::test_no_commit_flag_does_not_warn_when_clean` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestCommitFullLedgerChange::test_commits_dirty_whole_ledger` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestCommitFullLedgerChange::test_no_op_when_clean` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestCommitFullLedgerChange::test_no_commit_flag_warns_when_dirty` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestCommitFullLedgerChange::test_archive_cli_leaves_repo_clean` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestLedgerAutoCommitEnumeratedOverDispatchTable::test_dispatch_table_verbs_are_all_accounted_for` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestLedgerAutoCommitEnumeratedOverDispatchTable::test_verb_leaves_repo_clean` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 8 passed (from 8 evidence id(s))
- gates: 0 error(s), 575 warning(s), 724 waived
- error-findings: none (measured, zero errors)
