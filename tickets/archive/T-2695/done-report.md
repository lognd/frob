## Done report

Changed:
src/frob/tickets/_store.py (245 lines removed; migration functions extracted; ARCH102/F401 waived/fixed)
src/frob/tickets/_store_migrate.py (new module: migrate_to_ledger, migrate_v1_to_v2, migrate_missing_v2, _migrate_one_v2, _migrate_missing_ids, _split_done_report)
tests/unit/test_ticket_store.py (frob:tests anchor updated to new location)

Real seam found and extracted: `_store.py`'s one-shot, reversible
migration functions are a distinct pipeline phase from the rest of the
file's steady-state read/write/lock responsibility, with a distinct
consumer set (the `frob ticket migrate`/`frob ticket archive` CLI paths
and `tests/test_tickets_migration.py`, never the steady-state hot path).
Extracted verbatim into `src/frob/tickets/_store_migrate.py`, re-exported
from `_store.py`'s top-level import (per-name `# noqa: F401` matching
this repo's own `tickets/__init__.py` re-export convention) so every
existing `frob.tickets._store.migrate_*` call site keeps working.

Import-cycle avoidance: `_store_migrate.py` needs several `_store.py`
primitives, which in turn needs the new module's functions back for
re-export -- resolved via FUNCTION-LOCAL imports in `_store_migrate.py`
(this repo's own existing convention, e.g. `_land_cmd.py`/`_check_
chunking.py`), so there is no module-level cycle. Verified directly:
`import frob.tickets._store`/`_store_migrate`/`_archive`/`_setters` all
succeed standalone.

`src/frob/strata/_selfconform.py` (2290 lines, the ticket's other named
candidate) was investigated (full function inventory) and NOT split in
this batch: it needs a real three-layer architecture (shared observed-
capability-kinds computation used by 2+ SYS1xx rules / per-rule violation
classification / orchestration+waiver handling), genuinely larger
surgery than this batch, in this repo's OWN security self-conformance
checker where a rushed split risks the exact outcome the ticket's own
text warns against. Filed as its own ticket with the concrete plan
(T-2729, renumbers at land) and removed from this ticket's
scope -- not silently dropped, not waived with a shape-based excuse.

Side effects of the extraction, each investigated and disposed of
per-site (not blanket-forgiven):
- ARCH102 newly fired on `_store.py` (73 exports, 3 clusters) because the
  re-exported migrate_* names are now plain import bindings with no
  call-graph edges into the file's own helpers -- waived with the
  mechanism named explicitly (not a shape/count-based excuse).
- 5x AFFECT001 on the moved functions (doc anchors reference the OLD
  `_store.py` path) -- the doc file itself (docs/modules/tickets-data-
  storage.md) was under ANOTHER ticket's LIVE cross-worktree lease
  (T-2718) throughout this batch, so it could not be edited from this
  worktree. Waived with follow_up naming a new ticket (T-2730)
  that updates the anchors once the lease clears.
- WIRE001 on `migrate_missing_v2` (T-2355 function with genuinely no CLI
  wiring anywhere, confirmed by direct search -- pre-existing debt the
  diff-based novelty heuristic surfaced as "new"). Waived with follow_up
  naming a new ticket (T-2728) to wire it or delete it.
- 4x DRIFT002 on docs/modules/tickets-data-storage.md's own dangling
  `frob:describes` anchors -- COULD NOT be fixed or waived from this
  worktree: DRIFT002's Violation carries no symref (only file/line from
  the edge's ORIGIN, which is the doc file itself), so a matching waiver
  comment must live IN that doc file, which is under T-2718's live lease
  and cannot be edited right now. This is a genuine external blocker for
  this residual documentation-linkage piece, not a design choice --
  disclosed here, covered by the same T-2730 follow-up.

MEASUREMENT NOTE (per coordinator's autocrlf warning): all line counts
are from `wc -l`, cross-checked against LARGE001's own gate output
(`frob check --only archgate --json`), not a hand-rolled awk/grep count.

Evidence:
tests/test_tickets_migration.py::TestMigrateV1ToV2::test_golden_round_trip_semantic_equality
tests/test_tickets_migration.py::TestMigrateMissingV2::test_migrates_only_the_monofile_only_tickets
tests/unit/test_ticket_store.py::TestMigrateToLedger::test_moves_legacy_files_into_ledger
tests/unit/test_claims_and_store_batch6.py::TestTicketStoreWriteAndMigrate::test_migrate_to_ledger_moves_dir_files_into_ledger
(full touched-file run: 143 collected across tests/test_tickets_migration.py,
tests/unit/test_ticket_store.py, tests/unit/test_claims_and_store_batch6.py,
tests/unit/test_store_batch7.py -- 0 failed, post-split)

Filed: T-2729 (split _selfconform.py, concrete 3-layer plan),
T-2730 (update tickets-data-storage.md anchors once T-2718's
lease clears), T-2728 (wire migrate_missing_v2 or delete it)

Gates: `frob check --ticket T-2695` reduced to 2 error classes touching
this diff: ARCH103 on `_write_index_cache` (PRE-EXISTING, confirmed
present in the unscoped root baseline before this ticket started, line
number only shifted by the extraction) and the 4 DRIFT002 findings above
(external lease blocker, disclosed, follow-up filed). Every other
ARCH102/AFFECT001/WIRE001/F401 finding this diff introduced is resolved
or honestly waived with a specific, non-shape-based reason and a real
follow-up ticket where one was needed.

### Changed
```
 tickets/T-2695/ticket.md           | 47 +++++++++++++++++++++++--
 tickets/T-2728/ticket.md | 48 ++++++++++++++++++++++++++
 tickets/T-2729/ticket.md | 70 ++++++++++++++++++++++++++++++++++++++
 tickets/T-2730/ticket.md | 51 +++++++++++++++++++++++++++
 4 files changed, 213 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/test_tickets_migration.py::TestMigrateV1ToV2::test_golden_round_trip_semantic_equality` (pytest node id, verified passing when recorded)
- `tests/test_tickets_migration.py::TestMigrateMissingV2::test_migrates_only_the_monofile_only_tickets` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_store.py::TestMigrateToLedger::test_moves_legacy_files_into_ledger` (pytest node id, verified passing when recorded)
- `tests/unit/test_claims_and_store_batch6.py::TestTicketStoreWriteAndMigrate::test_migrate_to_ledger_moves_dir_files_into_ledger` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 46 error(s), 871 warning(s), 684 waived
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC002@src/frob/gates/_milestone.py, DOC006@tickets/T-2728/ticket.md, DOC006@tickets/T-2730/ticket.md, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII010@src/frob/deploy/_audit.py, PII012@src/frob/doctor.py, PII012@src/frob/serve/_socketd.py, PII012@tests/system/test_cli_doctor.py, PII012@tests/test_capability_registry.py, PII012@tests/test_doctor.py, PII012@tests/test_hook_diagnosis_nudge.py, PII012@tests/test_prework_parity.py, PII012@tests/test_vet.py, PII012@tests/unit/test_doctor_runner_t1276.py, RENDER001@src/frob/release/_cli.py, SEC004@tests/test_tickets_organization.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
