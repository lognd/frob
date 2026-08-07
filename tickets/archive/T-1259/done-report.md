## Done report

Delivers the T-1259 migration child's in-scope deliverables (design
section 7): the `migrate_v1_to_v2` engine, its golden round-trip
coverage, and the LEDGERV1001 deprecation gate. Final cutover
(deliverable 4) is deliberately deferred to a filed follow-up, per this
dispatch's explicit instruction not to flip this repo's live ledger
mid-drive.

`migrate_v1_to_v2(root)` (src/frob/tickets/_store.py) reads
tickets.md/tickets-archive.md via `_parse_ledger`, writes each ticket
into a v2-mode tickets/T-####/ticket.md (active) or
tickets/archive/T-####/ticket.md (already archived), splits any
embedded '## Done report' section out into its own done-report.md
(`_split_done_report`, reusing `_models._find_done_report_heading`/
`_done_report_section_end` rather than re-deriving the boundary logic),
and git-mvs any legacy tickets/attachments/<id>/ directory to the
ticket's own attachments/ via the existing `git_mv_dir` primitive.
It does NOT delete tickets.md/tickets-archive.md in the same call
(design section 7's explicit requirement) -- rollback is `rm -rf
tickets/T-*/ tickets/archive/`. A no-op (Ok(0)) once the repo is
already v2-mode.

Golden round-trip (tests/test_tickets_migration.py): a fixture ledger
covering every shape T-1259's acceptance[3] names -- a done ticket with
a real embedded Done report, a queued ticket with blocked_by, a ticket
with a real attachment file, an archived ticket, and a draft-id
ticket -- is migrated, then re-loaded via load_all/load_archive
(v2-mode auto-detected) and compared field-for-field
(model_dump(exclude={"body"})) against the original parse, plus the
Done report text itself is recovered via
`recover_done_report_why`/`read_done_report` and asserted equal.
11 tests total, all green.

LEDGERV1001 (src/frob/gates/_tickets_gate.py::_ledgerv1001_violations,
wired into tickets_gate): fires on a repo that actually HAS legacy
content (a real tickets.md or dir-mode tickets/*.md on disk -- not
_store_mode's fresh-repo default, which would otherwise false-positive
on every bare tmp_path test fixture across the existing gate test
suite) and is not yet v2-mode. WARN before the recorded sunset
(2027-02-02, docs/modules/tickets.md's new "Migration to v2" section),
ERROR after, mirroring DEPR004's escalation-after-expiry shape. Rule id
registered in _KNOWN_GATE_RULES (frob.gates._waive). Verified this
repo's own ledger (still v1, deliberately not cut over) now emits
exactly one LEDGERV1001 WARNING under a real `frob check` run, and does
not regress any existing gate test's exact-equality assertion (grepped
every `tickets_gate(...)` call site across tests/; the one bare-`tmp_path`
exact-equality assertion, tests/test_tickets_collision.py, has zero
legacy ledger content so LEDGERV1001 correctly stays silent there).

Cutover posture: deliberately NOT performed. Filed T-1491
(final cutover: flip fresh-repo default, delete v1 splice machinery)
recording the two preconditions design section 7 implies (a real quiet-
window migrate of this repo's own ledger, and an observed deprecation-
window interval) before that ticket can close. Filed T-1492
(CLI wiring: `frob ticket migrate --to v2`) since the CLI parser
(_cli_parsers/_ticket/_progress.py) and ticket_runner dispatch
(app/ticket_runner/_query.py, __init__.py) are outside this ticket's own
declared scope. Filed T-1490 (evaluate test-fixture-helper
WIRE001 disposition) per the conftest.py::_install_stackdump_handler/
T-1466 precedent for helpers only reachable from within their own test
file.

design/frob.strata gained: `migrate_v1_to_v2` in tickets_ledger's
interface attrs, `TestLedgerV1DeprecationGate`/`TestMigrateV1ToV2` in
testsuite's interface attrs, and testsuite's exec/fs.write/fs.read
`may` lists gained tests/test_tickets_migration.py -- added via `frob
ticket scope --add design/frob.strata` (SYS100/SYS104 self-audit gate
structural necessity for any new public symbol/test file, same
CLI-wiring-files shape T-0446 established, not scope creep).

Land-repair refresh (this session, coordinator dispatch): the prior land
attempt refused with "captured gate-state claim no longer holds post-merge
-- 1 NEW error finding(s)... WIRE001@src/frob/gates/_doclink_docanchor.py"
after merging main. Merged main again in this session (main had since
landed the WIRE001 relocated-symbol fixes referenced in this repo's own
recent history), rebuilt natives (`make core`), and re-ran `frob check
--only wire` plus `frob check --only sys --only ruff --only invariant
--only tickets`: 0 errors both times, no _doclink_docanchor.py WIRE001
finding present. Re-ran the 11 bound tests (tests/test_tickets_migration.py)
foreground: all passing post-merge. This Done report is refreshed to
recapture the current (post-merge) gate-state claim before retrying land.

### Changed
```
 design/frob.strata                           |   9 +-
 docs/modules/tickets.md                      |  57 +++++
 src/frob/gates/_tickets_gate.py              |  75 ++++++
 src/frob/gates/_waive.py                     |   7 +
 src/frob/tickets/_store.py                   | 132 +++++++++-
 tests/fixtures/tickets/sample-attachment.txt |   3 +
 tests/test_tickets_migration.py              | 351 +++++++++++++++++++++++++++
 tickets.md                                   | 341 ++++++++++++++++++++++++--
 8 files changed, 954 insertions(+), 21 deletions(-)
```

### Evidence
- `tests/test_tickets_migration.py::TestMigrateV1ToV2::test_golden_round_trip_semantic_equality` (pytest node id, verified passing when recorded)
- `tests/test_tickets_migration.py::TestMigrateV1ToV2::test_migrates_one_active_ticket_with_done_report` (pytest node id, verified passing when recorded)
- `tests/test_tickets_migration.py::TestMigrateV1ToV2::test_monofiles_left_in_place_reversible` (pytest node id, verified passing when recorded)
- `tests/test_tickets_migration.py::TestMigrateV1ToV2::test_attachment_moved_under_ticket_dir` (pytest node id, verified passing when recorded)
- `tests/test_tickets_migration.py::TestMigrateV1ToV2::test_archived_ticket_lands_under_archive_dir` (pytest node id, verified passing when recorded)
- `tests/test_tickets_migration.py::TestMigrateV1ToV2::test_draft_id_ticket_migrates_like_any_other` (pytest node id, verified passing when recorded)
- `tests/test_tickets_migration.py::TestMigrateV1ToV2::test_idempotent_no_v1_state_is_a_no_op` (pytest node id, verified passing when recorded)
- `tests/test_tickets_migration.py::TestLedgerV1DeprecationGate::test_monofile_mode_warns_before_sunset` (pytest node id, verified passing when recorded)
- `tests/test_tickets_migration.py::TestLedgerV1DeprecationGate::test_monofile_mode_errors_past_sunset` (pytest node id, verified passing when recorded)
- `tests/test_tickets_migration.py::TestLedgerV1DeprecationGate::test_v2_mode_repo_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_tickets_migration.py::TestLedgerV1DeprecationGate::test_no_ledger_content_at_all_is_silent` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 11 passed (from 11 evidence id(s))
- gates: 0 error(s), 1707 warning(s), 758 waived
- error-findings: none (measured, zero errors)

### Acceptance amendments
- [5] remove: removed 'GIVEN the final cutover has landed\nWHEN a real land runs\nTHEN it performs no monofile splice (T-1136 acceptance[1]), two agents\nlanding disjoint tickets produce no ledger merge conflict, and the\nTICK002/TICK006 draft-death classes described in the epic are\nstructurally impossible (draft directories are disjoint git objects,\nverified by a regression test reproducing the T-1115/T-1126/T-1127/\nT-1128 draft-death shape against v2 and asserting no draft is lost).' (reason: Final cutover (design section 7 deliverable 4) deliberately deferred: a live cutover of this repo's own ledger mid multi-agent drive risks every in-flight worktree, and the dispatch explicitly instructed NOT to do it this session. Filed T-1491 (final cutover: flip fresh-repo default, delete v1 splice machinery, the T-1115/T-1126/T-1127/T-1128 draft-death regression test) to carry this acceptance criterion forward once its stated preconditions (a real quiet-window migrate + an observed deprecation-window interval) hold.; logan, 2026-08-03)
- [0] remove: removed 'The migration child ticket, per T-1136\'s epic body ("migration is a\nseparate child... with golden round-trip tests") and design doc section\n7. Blocked by every design-implementing child (lock model, store\nbackend, renumber, archive, doable/index, land merge-story retirement) --\nmigration only makes sense once v2 is a fully working alternate mode.' (reason: Not a testable GIVEN/WHEN/THEN criterion -- background rationale explaining why this ticket is blocked_by the design-implementing children (T-1253..T-1258), duplicated verbatim from T-1136's epic body into the ticket's Description/blocked_by field already. No evidence id can bind to a why-this-exists statement; removing it here since it carries no acceptance content distinct from the ticket's own blocked_by/scope fields.; logan, 2026-08-03)
