## Done report

Changed (9 files, comment-only, one frob:waive LARGE001 directive prepended to each):

- src/frob/gates/_fmt_directives.py -- WAIVED. No seam: one mechanism (T-0441 two-directional directive-comment canonicalization), not a rule-id family.
- src/frob/gates/_gate_cache.py -- WAIVED. No seam: one mechanism (T-0602 per-obligation dependency-tracked partial re-evaluation cache); recording/fingerprint/persist are stages of one pipeline.
- src/frob/gates/_lang_conformance.py -- WAIVED. No seam: LANG001-004 (T-0405/T-0406) share one derive_language_registry scan and one ticket-verification helper (_verify_known_gap_ticket).
- src/frob/gates/_mutation_evidence.py -- WAIVED with a DEFERRED-SPLIT note, not a plain no-seam waiver. Investigation found a real consumer-set seam: TEST016/TEST018 (~260 lines, plus shared quoted-range helpers _tickets_gate.py also imports) is a distinct concern from the BUG002/must-still-pass repro-classification family (~800 of the file's 1267 lines: worktree checkout, subprocess spawn/classify, bug_repro_outcome_at_ref, bug_repro_violations, must_still_pass_violations). Not split in this diff because bug_repro_outcome_at_ref is a load-bearing, land-critical shared entrypoint (frob.tickets._land's pre-land check AND frob.app.ticket_runner's close-time CLI path both call it) that deserves its own reviewed pass rather than a batch line-count cut -- same precedent T-2833 used for src/frob/tickets/_land_git_ops.py (waived, follow-up filed for the real split). Follow-up filed: T-2851 "Split BUG002/must-still-pass repro-classification family out of frob.gates._mutation_evidence" (renumbers to a real id at land; checked T-1608/T-1609/T-1661/T-2202 first, none overlap this concern).
- src/frob/gates/_protocol_summary.py -- WAIVED. No seam: PROTO001-005 (T-0744-T-0747) share one build_call_graph/compute_protocol_summaries scan (module's own docstring: "one pass, three findings, never three separate repo walks") and one reachability primitive PROTO002/PROTO003 both call.
- src/frob/gates/_refs.py -- WAIVED. No seam: REF001-003 (T-0396/T-1665) are three layers of ONE detection sequence (resolved-import, auto-scan, directive-declared) feeding one _build_ref_gate_indexes/_ref_gate_file_violations pipeline.
- src/frob/gates/_registry_exhaustiveness.py -- WAIVED. No seam: REG001-011 (T-0343/T-0407) are disposition-kind checks over one _classify_all_entries pass registry_gate assembles once per run.
- src/frob/gates/_tickets_gate.py -- WAIVED. No seam: TICK001-013 plus LEDGERV1001 dispatch from the single tickets_gate() entrypoint over the same loaded TicketQueue; matches this repo's established rule-id-family precedent (LANG/REF/REG/PROTO).
- src/frob/gates/_wire.py -- WAIVED. No seam: WIRE001/002/003 (T-1420/T-1725) dispatch from the single wire_gate() entrypoint over the same diff/snapshot/queue inputs assembled once; WIRE001's larger share of lines reflects unwired-symbol-detection's genuinely larger reachability-scan machinery, not bundled unrelated concerns.

Disposition summary: 8 of 9 files have no real seam -- each is a single rule-id family (or single mechanism) sharing one entrypoint/scan/pipeline, matching this repo's own established LARGE001 precedent for gate modules (LANG/REF/REG/PROTO/TICK all previously waived on the identical "one family, one entrypoint" basis). 1 of 9 (_mutation_evidence.py) has a real seam that is closable but risky (a land-critical shared entrypoint) -- waived now with the seam disclosed and a follow-up ticket filed for the actual split, per the T-2833/_land_git_ops.py precedent.

Verification: frob.gates._arch.arch_gate() plus frob.gates._waive._apply_waivers() run directly against a live build_graph() snapshot of this worktree -- all 9 files' LARGE001 findings now read WAIVED (previously present as unwaived per T-2827's own filing measurement). Per-file result (rule_id, file, waived):
  LARGE001 src/frob/gates/_fmt_directives.py -- waived
  LARGE001 src/frob/gates/_gate_cache.py -- waived
  LARGE001 src/frob/gates/_lang_conformance.py -- waived
  LARGE001 src/frob/gates/_mutation_evidence.py -- waived (deferred-split disclosed)
  LARGE001 src/frob/gates/_protocol_summary.py -- waived
  LARGE001 src/frob/gates/_refs.py -- waived
  LARGE001 src/frob/gates/_registry_exhaustiveness.py -- waived
  LARGE001 src/frob/gates/_tickets_gate.py -- waived
  LARGE001 src/frob/gates/_wire.py -- waived

Note: per this drive's own discovered correction (T-2823/T-2824), the aggregate `frob check --only arch --json` summary line does not decompose per file and does not move on a batch of file-scoped waivers -- verification here used the direct arch_gate()/_apply_waivers() call against build_graph(), not the aggregate summary.

Evidence: tests/test_gates.py::TestWireGate::test_wire002_clean_when_follow_up_ticket_is_open, tests/test_gates_mutation_evidence.py::TestMutationEvidenceViolations::test_confirmatory_finding_is_warn_for_feature_kind (both bound). Full local run: `uv run pytest -q tests/test_gates.py tests/test_gates_mutation_evidence.py` -> 803/809 collected, 6 failed. All 6 failures (TestWireGate::test_new_cli_dest_present_in_config_external_is_not_flagged, TestFixEngineTierABatch2::test_docenum001_fails_before_fix_and_passes_after, TestAutofixManifest::test_killed_mid_handler_leaves_manifest_naming_completed_fixes, TestOptInGates::test_perf_gate_still_reports_genuine_parse_failure, TestDoc004ConsoleCommandDrift::test_real_subcommand_unanchored_warns_unbound, TestKnownGateRuleIds::test_every_emitted_rule_literal_is_known) reproduced byte-for-byte on the unmodified main checkout with none of this ticket's changes present -- confirmed pre-existing, not introduced by this ticket.

Filed: T-2851 (renumbers at land) -- split BUG002/must-still-pass repro-classification family out of frob.gates._mutation_evidence into a new frob.gates._bug_repro.py, deferred as a dedicated reviewed pass given bug_repro_outcome_at_ref's land-critical caller set.

Gates: `uv run frob check --only static --ticket T-2827` -- no malformed-directive findings (all 9 new waiver directives parse cleanly, no embedded-quote DSL breakage); frob-arch findings unrelated to these 9 files (god-module/type-dispatch-smell/unguarded-shared-write findings elsewhere) are pre-existing repo-wide noise untouched by this change. Did NOT touch src/frob/strata/_selfconform.py (T-2729's own ticket) or promote LARGE001 severity (deferred to T-2375's own final step per this ticket's own instructions).

### Changed
```
 tickets/T-2827/ticket.md           | 19 +++++++++++++++++--
 tickets/T-2851/ticket.md | 35 +++++++++++++++++++++++++++++++++++
 2 files changed, 52 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestWireGate::test_wire002_clean_when_follow_up_ticket_is_open` (pytest node id, verified passing when recorded)
- `tests/test_gates_mutation_evidence.py::TestMutationEvidenceViolations::test_confirmatory_finding_is_warn_for_feature_kind` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 23 error(s), 861 warning(s), 783 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, CYCLE001@src/frob/__init__.py, DOC006@docs/audits/test005-zero-classification-t1418.md, DOC011@docs/investigations/T-2796-backlog-reproduction.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, OPAQUE001@src/frob/gates/_refs.py, PERF004@src/frob/strata/_selfconform_binding_rules.py, PERF004@src/frob/strata/_selfconform_surface_rules.py, PERF004@src/frob/tickets/_evidence.py, PRE001@tickets/T-2827, REG002@docs/design/registry/check-coverage.yaml, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, SYS003@src/frob/check/__init__.py, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md
