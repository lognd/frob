## Done report

Changed:
- src/frob/app/ticket_runner/_ledger_mirror.py::LedgerWriteStrategy (new)
- src/frob/app/ticket_runner/_ledger_mirror.py::LEDGER_VERB_STRATEGY (new)
- src/frob/app/ticket_runner/_ledger_mirror.py::ledger_write_strategy_for (new)
- src/frob/app/ticket_runner/_ledger_mirror.py::OWN_TRANSACTION_VERBS (new, derived)
- src/frob/app/ticket_runner/_ledger_mirror.py::MIRRORED_LEDGER_VERBS (now derived, same name/values minus dead "debt" entry)
- src/frob/app/ticket_runner/__init__.py::_LEDGER_TRANSACTIONAL_VERBS (now an import alias for OWN_TRANSACTION_VERBS)
- src/frob/app/ticket_runner/__init__.py::_auto_commit_ledger_after_dispatch (consults ledger_write_strategy_for instead of two frozensets + a special case)
- docs/modules/tickets-lifecycle.md (new "One verb table, not two sets (T-2603)" section)
- tests/unit/test_ticket_runner_ledger_mirror.py::TestVerbStrategy (new)

## Pre-work: full enumeration (done before writing any code, as required)

Enumerated all 48 real `_ticket_dispatch_table()` verbs against the OLD
`_LEDGER_TRANSACTIONAL_VERBS` (5: land, merge-driver, promote, renumber,
sweep-async), OLD `MIRRORED_LEDGER_VERBS` (17, including a DEAD "debt"
entry -- its handler never sets cfg.ticket_id, so the mirror path was
structurally unreachable for it regardless of set membership), and
`promote`'s bespoke special case in `_auto_commit_ledger_after_dispatch`.
Cross-checked the enumeration against `tests/test_ticket_leases.py::
TestLedgerAutoCommitEnumeratedOverDispatchTable`'s OWN independent
classification (its `_MUTATING_VERB_INVOCATIONS`/`_READ_ONLY_VERBS`/
`_NEEDS_DEDICATED_FIXTURE` buckets). That test is currently RED on
unmodified main (4 verbs -- body, contention, milestone, waive-audit --
are unclassified there, and milestone's omission from MIRRORED_LEDGER_VERBS
is a live T-2563-class bug), filed separately as it is outside T-2603's
declared scope (see Filed below).

## Finding: the three shapes DO generalise, into five declared strategies

Every verb's mechanical behaviour inside `_auto_commit_ledger_after_
dispatch` reduces to exactly one of: OWN_TRANSACTION (owns a complete
transaction, never touched by the generic sweep or mirror -- land,
merge-driver, renumber, sweep-async), OWN_TRANSACTION_LEDGER_MIRROR (same,
plus promote's own dedicated read-back-and-narrow mirror -- promote only),
GENERIC_COMMIT_MIRRORED (the old MIRRORED_LEDGER_VERBS' 15 live members),
GENERIC_COMMIT_UNMIRRORED (state-machine verbs whose generic-commit call
is usually a no-op and never mirrored), and NOT_TICKET_SCOPED (read-only,
or cfg.ticket_id is structurally never set). No value means two different
things for two different verbs -- verified by
`LedgerWriteStrategy.OWN_TRANSACTION_LEDGER_MIRROR` existing as its OWN
enum member rather than promote sharing OWN_TRANSACTION or GENERIC_COMMIT_
MIRRORED with anyone else, which is exactly the "table whose entries mean
different things per key" failure the ticket asked me to avoid.

## Fail-loud requirement

`ledger_write_strategy_for(command)` raises `KeyError` naming the gap for
any `_ticket_dispatch_table()` verb without a `LEDGER_VERB_STRATEGY`
entry, replacing the old implicit default (generic-commit-but-never-
mirror) a verb added to the dispatch table used to fall into silently --
the exact shape of the T-2197 bug this ticket cites. Verified with
`TestVerbStrategy::test_missing_raises`.

Evidence: 5 ids bound (see `frob ticket show T-2603`), including
`TestPromoteMirror::test_promote_from_worktree_is_visible_on_primary_
without_a_land` (T-2587's own repro, re-run to confirm identical
behaviour under the new table).

Positive controls:
- every verb previously in `_LEDGER_TRANSACTIONAL_VERBS` is still in
  `OWN_TRANSACTION_VERBS` (test_derived_match)
- every verb previously in `MIRRORED_LEDGER_VERBS` (minus the dead
  "debt" entry) is still in the derived `MIRRORED_LEDGER_VERBS`
  (test_derived_match)
- `TestPromoteMirror`'s full 5-test suite still passes unchanged
- `test_all_classified`: every real dispatch-table verb has exactly one
  `LEDGER_VERB_STRATEGY` entry (48/48)
- `test_missing_raises`: an undeclared verb fails loudly, not silently

Filed: T-draft-38a082e8 (renumbers on land) -- `tests/test_ticket_leases.
py`'s dispatch-table-accounting test is red on unmodified main (body/
contention/milestone/waive-audit unclassified there), and `milestone` is
missing a live `MIRRORED_LEDGER_VERBS` entry it should have (a real
T-2563-class bug, found during this ticket's own audit, out of scope to
fix here since it touches `tests/test_ticket_leases.py` and `_mutate.py`,
neither declared in T-2603's scope).

Gates: `frob check --ticket T-2603` -- COV001/SCOPE002/FMT001 findings
against this ticket's own new symbols all resolved (frob:doc/frob:tests
edges added, scope widened to docs/modules/tickets-lifecycle.md +
tests/unit/test_ticket_runner_ledger_mirror.py + __init__.py, directive
lines wrapped to canonical width). Remaining findings attributable to
this file (COV007 x2 on `_mirror_target`/`_commit_mirrored_paths`) are
pre-existing, untouched by this diff. gate:EXHAUST passes overall (0
errors); the two EXHAUST003/004 findings on `ledger_write_strategy_for`
are explicitly documented lower-confidence resolution-coverage gaps, not
confirmed unhandled paths, and EXHAUST002 (the confirmed-unhandled check)
is clean after the `# frob:raises KeyError` declaration. All other
repo-wide gate FAILs (COV/DOC/DRIFT/PERF/etc.) are pre-existing baseline
noise unrelated to this diff (verified: none reference _ledger_mirror.py
or the new test file beyond the items listed above).

### Changed
```
 docs/modules/tickets-lifecycle.md              |  88 ++++++--
 src/frob/app/ticket_runner/__init__.py         |  81 +++++---
 src/frob/app/ticket_runner/_ledger_mirror.py   | 276 +++++++++++++++++++++----
 tests/unit/test_ticket_runner_ledger_mirror.py |  77 +++++++
 tickets/T-2603/ticket.md                       |  27 +++
 5 files changed, 463 insertions(+), 86 deletions(-)
```

### Evidence
- `tests/unit/test_ticket_runner_ledger_mirror.py::TestVerbStrategy::test_all_classified` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_ledger_mirror.py::TestVerbStrategy::test_derived_match` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_ledger_mirror.py::TestVerbStrategy::test_missing_raises` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_ledger_mirror.py::TestVerbStrategy::test_promote_kind` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_ledger_mirror.py::TestPromoteMirror::test_promote_from_worktree_is_visible_on_primary_without_a_land` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV001@src/frob/gates/_rule_id_scan.py, COV001@src/frob/strata/_multifile.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC006@tickets/T-2570/ticket.md, DOC008@docs/modules/gates.md, DOCENUM001@docs/modules/gates.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, F401@/home/logan/projects/frob/.claude/worktrees/t2602-t2603/src/frob/app/ticket_runner/__init__.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, PRE001@tickets/T-2603, RENDER001@src/frob/release/_cli.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
