## Done report

REWORK (reviewer round 2, 2026-07-23): the first pass over-exported. Every decision below was redone from scratch by applying one mechanical test to each symbol: does any file OUTSIDE the owning package (frob.strata or frob.tickets) import it, with test files excluded from counting as a consumer. No import from outside the package, regardless of intra-package cross-module use or field-type relationships to an already-exported type, demotes to a leading underscore. This moved 6 of the 9 strata decisions and 23 of the 33 tickets decisions from export to demote relative to the rejected first pass.

Revised strata table (3 export, 6 demote): scan_text_for_fingerprints and FingerprintHit export -- consumed by frob.gates._cve_fingerprint_scan.py, a different package. HostAcl exports -- consumed by frob.deploy._generate_windows.py. AclDecl demotes to _AclDecl -- its only consumer is _ast.py's own NodeDecl/StoreDecl field declarations in the same file; NodeDecl itself has no external consumer either, so there was never an external need for AclDecl's own visibility. observed_call_names demotes to _observed_call_names -- sole consumer is _threat.py, inside strata. check_regulation_caught_by_integrity and check_cmpl_registry_unit_dispositions demote -- each consumed only by its own module's caller (evaluate_compliance / check_cmpl_registry) plus tests; the frob:doc anchor they carried was a page-level architecture anchor shared with several still-public siblings on the same page, not itself evidence of external need. caught_by_unresolved_tokens and check_caught_by_integrity demote -- consumed by _compliance.py and _audit.py respectively, both inside strata, never imported from outside the package.

Revised tickets table (10 export, 23 demote): exported -- LeaseError, lease_age_seconds, is_lease_ttl_expired, leases_dir, sweep_worktrees, resolve_lease (all consumed by frob.app.ticket_runner.py / worktree_runner.py / check_runner.py / frob.gates / frob.serve._daemon.py, genuinely outside frob.tickets); ConfirmatoryFinding, MutationEvidenceError, check_ticket_mutation_evidence (consumed by frob.gates._mutation_evidence.py); agent_env_exports (consumed by frob.app.agent_runner.py). Demoted -- the entire _brief.py family (PlaybookSection, parse_playbook_sections, load_playbook_sections, infer_verify_commands, gate_baseline_summary, current_version): every consumer is compose_brief in the same module, or tests; the shared frob:doc anchor across all of them was this pipeline's own architecture page, not an external-need signal. The entire _journal.py family (JournalError, LandIntent, journal_dir, write_intent, clear_intent, read_all_intents): consumed by _land.py and _reconcile.py, both inside frob.tickets -- intra-package, not external. git_common_dir, list_agent_worktrees, LeaseRecord, WorktreeSweepError, WorktreeVerdict demote: git_common_dir and list_agent_worktrees are each called by exactly one sibling function in the same module (leases_dir, sweep_worktrees); LeaseRecord/WorktreeSweepError/WorktreeVerdict are the payload/error types those and other now-exported functions return, but per the mechanical test literally nothing outside frob.tickets imports the type names themselves (callers consume the Result without ever needing to spell the type) -- demoted despite being return-type payloads of exported functions, per the reviewer's explicit instruction to apply the test mechanically rather than carve out a field-type exception. omit_empty_collections demotes: sole caller is Ticket._omit_empty_collections_on_dump in the same module; its "public-api"-flavored frob:doc anchor was not itself evidence of external need, matching the reviewer's own stated position on this exact symbol. changed_line_ranges, evidence_test_ids, touched_python_files demote from the _mutation_evidence.py family: each is called only by this module's own check_ticket_mutation_evidence, which is the actual exported cross-package entry point; their shared frob:doc anchor was the same pipeline-level page as check_ticket_mutation_evidence's own anchor, not independent evidence of external need. check_ledger_id_integrity (_store.py) demotes: its only consumer is _land.py, inside frob.tickets. lock_path (_store.py) was already correctly demoted to _lock_path in the first pass and is unchanged here.

Fixed the dangling reference the reviewer flagged: src/frob/tickets/_land.py:78's comment referenced `_store.lock_path` by its pre-rename public name; updated to `_store._lock_path`. Re-grepped every demoted old name across src/ AND tests/ AND comment prose (not just import statements) this time -- found and fixed prose references in _threat.py, _compliance.py, _audit.py, tests/unit/strata/test_threat.py, tests/unit/strata/test_audit.py, tests/system/test_spawn_budget.py, and docs/modules/tickets.md's two `<!-- frob:describes -->` anchors for evidence_test_ids/touched_python_files (a DRIFT002 finding caught the second miss).

Extended T-0601's scope to cover every test file the demotions' caller updates reached into (17 additional test files plus tests/system/test_spawn_budget.py, recorded via `frob ticket scope --add` with reasons each time) -- these are genuinely part of this rework's diff, not scope creep for its own sake.

Final exports counts, re-measured directly via frob.check._python._run_exports after the full rework: frob-exports(src/frob/strata) and frob-exports(src/frob/tickets) report 0 unresolved findings (neither package's line appears in a fresh `frob check --ticket T-0601 --only static` run, confirmed by direct diff against every OTHER package's frob-exports(...) line, which does still appear for arch/lang/perf/scaffold/serve/testing/vet as expected -- those are out of scope).

Targeted test suite (unit/strata/, tickets test files listed in the Done-report evidence plus every newly-scoped file) passed in full, exit 0, except the same four pre-existing, out-of-scope failures already disclosed in the prior round (tests/unit/strata/test_export_golden.py's three cases and test_selfconform.py's SYS100 finding on mutate/deploy) -- tracked at T-0860, not this ticket's to fix.

Ran the chunked `frob check --ticket T-0601` loop (lint, static, gates-fast, gates-native, gates-security) to a clean gate-summary of 0 errors across every stage after two follow-up fixes: a DRIFT002 pair (the two stale docs/modules/tickets.md anchors above) and a tests/system/test_spawn_budget.py frob:tests directive still naming git_common_dir by its old public name, both caught by the chunked gates-fast pass and fixed in place.

### Changed
```
 docs/modules/graph.md                            |   4 -
 docs/modules/tickets.md                          |  12 +-
 src/frob/gates/__init__.py                       |  21 +-
 src/frob/gates/_dead_symbols.py                  |   3 +-
 src/frob/gates/_fmt_directives.py                |   2 +-
 src/frob/gates/_protocol_summary.py              |   9 +-
 src/frob/graph/__init__.py                       |  27 +-
 src/frob/graph/cache.py                          |  11 +-
 src/frob/process/parsers/__init__.py             |   2 +
 src/frob/registry/__init__.py                    |   3 +
 src/frob/strata/__init__.py                      |  13 +-
 src/frob/strata/_ast.py                          |  10 +-
 src/frob/strata/_audit.py                        |   8 +-
 src/frob/strata/_code_binding.py                 |   5 +-
 src/frob/strata/_compliance.py                   |  34 +-
 src/frob/strata/_threat.py                       |  26 +-
 src/frob/tickets/__init__.py                     |  28 +-
 src/frob/tickets/_brief.py                       |  55 +--
 src/frob/tickets/_journal.py                     |  51 +--
 src/frob/tickets/_land.py                        |  16 +-
 src/frob/tickets/_leases.py                      |  88 +++--
 src/frob/tickets/_models.py                      |   6 +-
 src/frob/tickets/_mutation_evidence.py           |  29 +-
 src/frob/tickets/_reconcile.py                   |  10 +-
 src/frob/tickets/_store.py                       |  25 +-
 tests/system/test_spawn_budget.py                |   8 +-
 tests/test_gates.py                              |   6 +-
 tests/test_graph.py                              |  11 +-
 tests/test_registry_reconciliation_compliance.py |   2 +-
 tests/test_serve_daemon.py                       |   8 +-
 tests/test_ticket_journal.py                     |  48 +--
 tests/test_ticket_leases.py                      |  12 +-
 tests/test_ticket_leases_cross_worktree.py       |   6 +-
 tests/test_ticket_reconcile.py                   |  12 +-
 tests/test_ticket_runner_archive_force.py        |   5 +-
 tests/test_tickets.py                            |  16 +-
 tests/test_tickets_brief.py                      |  34 +-
 tests/test_tickets_dispatch_stale.py             |   8 +-
 tests/test_tickets_lease_overlay.py              |  10 +-
 tests/test_tickets_leases.py                     |   8 +-
 tests/test_tickets_mutation_evidence.py          |  14 +-
 tests/unit/strata/test_audit.py                  |   2 +-
 tests/unit/strata/test_code_binding.py           |  22 +-
 tests/unit/strata/test_compliance.py             |  44 +--
 tests/unit/strata/test_threat.py                 |  58 +--
 tests/unit/test_ticket_store.py                  |   8 +-
 tickets.md                                       | 478 ++++++++++++++++++++++-
 47 files changed, 958 insertions(+), 360 deletions(-)
```

### Evidence
- `tests/test_tickets_brief.py::TestParsePlaybookSections::test_parses_numbered_headings_only` (pytest node id, verified passing when recorded)
- `tests/test_ticket_journal.py::TestWriteIntent::test_write_then_read_round_trips` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestSweepWorktrees::test_clean_no_lease_removed` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases_cross_worktree.py::TestGitCommonDir::test_shared_across_linked_worktrees` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestEmptyCollectionOmission::test_dict_without_empty_collections_returned_unchanged` (pytest node id, verified passing when recorded)
- `tests/test_tickets_mutation_evidence.py::TestCheckTicketMutationEvidence::test_confirmatory_test_flagged` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestSpliceLedgerIdDropGuard::test_render_that_would_drop_an_id_is_refused` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_store.py::TestLockPath::test_lock_path_under_frob_dir` (pytest node id, verified passing when recorded)
- `tests/test_worktree_guard.py::TestAgentEnvExports::test_resolves_worktree_root` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_compliance.py::TestRegulationCaughtByIntegrity::test_caught_by_naming_present_control_discharges` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_code_binding.py::TestObservedCallNames::test_bare_call_name_is_observed` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_compliance.py::TestCmplRegistry::test_deferred_disposition_is_refused` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_threat.py::TestCaughtByUnresolvedTokens::test_unknown_rule_id_is_unresolved` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 13 passed (from 13 evidence id(s))
- gates: 0 error(s), 1009 warning(s), 306 waived
- error-findings: none (measured, zero errors)
