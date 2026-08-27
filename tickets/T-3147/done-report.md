## Done report

Changed: none (measurement-only ticket; no src/ or test/ files touched).

Filed: T-3156 ("D-02 has no legitimate evidence route for
docs-only bug-kind or Rust-only tickets") -- the forward gap this audit
exposed. Verify its real id on main before citing it elsewhere.

Kind changed bug -> docs (triage_changes, reasoned) partway through this
ticket: a pure audit/measurement close has no code surface, and post-
T-3141 the ONLY legitimate D-02 route for that shape is the docs/ux
cmd: evidence channel (T-0215) -- exactly the gap T-3156
documents. This ticket hit its own finding while trying to close itself;
noted rather than hidden.

## Method
Independent of D-02 entirely: for each DONE ticket, computed whether
`frob.gates.evidence_covers_scope`'s real logic (TESTS edge, or evidence
file directly in `ticket.scope`) would pass using ONLY `ticket.scope`
(i.e. with the current `evidence_scope` field excluded). Separately
computed which `evidence_scope` entries are backed by a real, reasoned
`demote_to_evidence_only` migration (visible in `scope_changes` as an
`op: remove` entry for that same glob, with a reason) versus present in
`evidence_scope` with no such backing -- the latter can only be a T-1944
auto-widen artifact, since that was the only other code path that ever
wrote to the field before the T-3141 fix. A ticket is FLAGGED when it
carries an unbacked evidence_scope glob AND scope-only D-02 fails.

Cross-checked every flagged ticket against `frob.graph.reach.
classify_evidence_reach` (T-3046), and against each ticket's own
done-report prose, to resolve the reach classifier's UNKNOWN verdicts
(non-Python scope, or scope with no on-disk file) that neither the
gate-logic re-derivation nor the reach classifier alone can settle.

## Population
48 DONE tickets in the ledger carry a non-empty `evidence_scope`. 18 of
those are flagged (unbacked glob + scope-only D-02 fails); all 18 landed
2026-08-25..2026-08-27, inside the T-1944/T-3141 window (2026-08-10..
2026-08-27). No flagged ticket predates T-1944 (2026-08-10) -- consistent
with the mechanism: the field did not exist as a self-cover route before
that commit.

## Agree/disagree matrix vs classify_evidence_reach (T-3046)
| Reach verdict          | Count | Tickets |
|-------------------------|-------|---------|
| REACHES                 | 4     | T-2645, T-2914, T-2970, T-3093 |
| DOES_NOT_REACH           | 2     | T-2956, T-3064 |
| UNKNOWN (non-Python scope) | 3  | T-3005, T-3007, T-3056 |
| UNKNOWN (scope matches no file on disk) | 9 | T-2384, T-2804, T-2892, T-2893, T-2902, T-2909, T-2946, T-2955, T-3060 |

The two instruments AGREE (both flag a real problem, or both clear the
same tickets as fine) on the REACHES group -- 4 tickets where D-02's
tautology was harmless because the evidence is genuinely related, just
not formally declared in `scope`. They DISAGREE in the interesting
direction on the other 14: D-02's tautology mechanically let all 18
through regardless of relation, while the reach classifier only had a
verdict to offer on 6 of them (4 REACHES + 2 DOES_NOT_REACH); the other
12 are structurally outside what a Python call-graph tool can see
(Rust code, or scope that names doc/ticket files with no call graph at
all). That 12-of-18 UNKNOWN rate is itself the finding worth flagging:
neither instrument alone resolves most of this population -- direct
done-report inspection was required.

## Per-ticket disposition

FINE ON INSPECTION (18/18 -- no ticket in this population needs
reopening or re-evidencing):

- T-2645, T-2914, T-2970, T-3093: reach classifier independently
  confirms the bound evidence really exercises the scoped symbol
  (direct-call match). D-02's tautology was inert here.
- T-2956: `frob:no-behavior-change` directive present in the ticket
  body -- DOES_NOT_REACH is the EXPECTED outcome for a documentation-
  of-a-waiver-decision change with a deliberately-unchanged designated
  repro test, not evidence of laundering.
- T-3064: already independently resolved. T-3087's disposition (see
  T-3064's own ticket.md note, 2026-08-27) explicitly left it CLOSED
  rather than reopened, because the real work was redone under T-3086
  with correct scope; reopening T-3064 now would race T-3086's own
  lease. Nothing for this ticket to do.
- T-3005, T-3007: CONFIRMED -- the D-02 tautology is exactly what let
  these close, verifying the pattern already suspected before this
  audit (per this ticket's brief). Both done-reports disclose real
  `cargo test` evidence in prose (T-3005: 18/155 passed; T-3007:
  168/170 passed) that frob has no channel to bind or verify -- the
  bound pytest ids are an acknowledged "proves the crate still
  compiles" placeholder, not a claim of functional coverage, and both
  done-reports say so explicitly. Honest and disclosed, not laundered;
  the underlying gap (no Rust/cargo evidence channel) is real and is
  part of T-3156.
- T-3056: same Rust-scope shape as T-3005/T-3007, same disclosed "no
  pytest surface of its own" placeholder-evidence convention.
- T-2384, T-2804, T-2892, T-2893, T-2902, T-2909, T-2946, T-2955,
  T-3060: docs/ledger-only tickets. Each done-report explicitly states
  "no code change" / "no pytest surface of its own" and names the
  actual on-disk diff (a ticket.md field, a doc file, an archived
  done-report correction) as the real deliverable -- independently
  verifiable by reading the ticket's own scope diff, not by any
  evidence binding. 6 of these 9 (T-2384, T-2804, T-2893, T-2902,
  T-2946, T-2955) are `bug`-kind, meaning they had NO legitimate D-02
  route at all post-fix (not `cmd:`, wrong kind; not a TESTS edge, no
  code; not `demote_to_evidence_only`, the bound file was never in
  `scope`) -- this is the second half of T-3156.

UNKNOWN as a real, held state (not silently passed or failed): the 12
non-REACHES/non-DOES_NOT_REACH tickets above were resolved to "fine" by
manual done-report inspection, NOT by either automated instrument --
that gap in coverage is itself recorded here rather than assumed away.

## Bottom line
17-day exposure window, 733 evidence bindings measured repo-wide by
T-3046 at 95.5% REACHES / 1.2% DOES_NOT_REACH / 3.3% UNKNOWN. This
ticket-level audit of the specific closes that structurally depended on
the tautology finds 18 candidates, 0 requiring reopening or
re-evidencing. The damage is real but narrow: it never let a genuinely
unrelated close through undetected (the 2 DOES_NOT_REACH cases were
each independently disclosed/resolved on their own merits before this
audit even started); its actual effect was to quietly cover for two
structural gaps in D-02 itself (no Rust evidence channel, no route for
bug-kind no-code tickets) that were previously invisible because the
tautology papered over them. Filed as T-3156 rather than
fixed here (design decision, out of this ticket's measurement-only
scope).

Gates: `frob check --only scope --ticket T-3147` -- ticket has no
code scope to check. D-02 satisfied via the docs-kind cmd: evidence
channel (see kind-change note above).

### Changed
```
 tickets/T-3147/ticket.md           | 20 +++++++-
 tickets/T-3156/ticket.md | 96 ++++++++++++++++++++++++++++++++++++++
 2 files changed, 114 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_measure_evidence_reach.py::TestMeasureEvidenceReachMain::test_runs_clean_over_a_minimal_ticket_ledger` (pytest node id, verified passing when recorded)
- `cmd:uv run python /tmp/claude-1000/-home-logan-projects-frob/79c6402d-b401-4652-bea7-f81df1be9322/scratchpad/audit_d02.py exit=0 sha256=13b392782051` (cmd evidence, exit=0)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 118 error(s), 677 warning(s), 872 waived
- error-findings: ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/refactor/_verify.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@.claude/hooks/frob-suggest.py, COV001@scripts/branch_stranded_work_analysis.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV007@.claude/hooks/frob-suggest.py, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC005@docs/modules/cli.md, DOC006@tickets/T-2962/ticket.md, DOC006@tickets/T-3139/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_process_reap.py, DOC007@tests/unit/test_reopen_ticket.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@docs/modules/gates.md, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_process_reap.py, DRIFT002@tests/unit/test_reopen_ticket.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, PERF004@.claude/hooks/frob-suggest.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, REF001@.claude-scratch/T-3122-close-guard-repro-capture.md, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/conftest.py, SEC110@tests/test_worktree_guard.py, SELFAUDIT001@design, SUPPRESS001@src/frob/app/_config_external.py, SYS003@scripts/branch_stranded_work_analysis.py, SYS003@src/frob/app/vet_runner.py, SYS003@src/frob/gates/_docblocks_refs.py, SYS003@src/frob/gates/_fix_engine_tier_c.py, SYS003@src/frob/gates/_fuzz.py, SYS003@src/frob/gates/_gate_cache.py, SYS003@src/frob/gates/_models.py, SYS003@src/frob/gates/_wire.py, SYS003@src/frob/vet/_models.py, SYS003@tests/gates/test_rule_id_scan_branches.py, SYS003@tests/gates/test_tdd_order.py, SYS003@tests/test_arch_gate.py, SYS003@tests/test_ci_report.py, SYS003@tests/test_ci_validity.py, SYS003@tests/test_docblocks_gate.py, SYS003@tests/test_docptr_gate.py, SYS003@tests/test_fuzz.py, SYS003@tests/test_gates_suppress.py, SYS003@tests/test_ghio.py, SYS003@tests/test_lang_conformance_gate.py, SYS003@tests/test_narrative_migrate.py, SYS003@tests/test_pii_structural_gate.py, SYS003@tests/test_refs_gate.py, SYS003@tests/test_registry_exhaustiveness.py, SYS003@tests/test_registry_staleness.py, SYS003@tests/test_secrets_gate.py, SYS003@tests/test_todo_fmt_gate.py, SYS003@tests/test_vet.py, SYS003@tests/unit/gates/test_doc011.py, SYS003@tests/unit/gates/test_refs.py, SYS003@tests/unit/gates/test_sys_selfaudit.py, SYS003@tests/unit/security/test_redact.py, SYS003@tests/unit/strata/test_cve_fingerprint_scan.py, SYS003@tests/unit/test_arch_table_schema.py, SYS003@tests/unit/test_docblocks_table_schema.py, SYS003@tests/unit/test_dup_graph_table_schema.py, SYS003@tests/unit/test_flag_coverage_gate.py, SYS003@tests/unit/test_gates_table_schema.py, SYS003@tests/unit/test_native_table_schema.py, SYS003@tests/unit/test_profile_table_schema.py, SYS003@tests/unit/test_refs_schema.py, SYS003@tests/unit/test_test_table_schema.py, SYS003@tests/unit/test_testing_table_schema.py, SYS003@tests/unit/test_toplevel_scalar_schema.py, SYS003@tests/unit/vet/test_taint.py, TEST001@scripts/branch_stranded_work_analysis.py, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py, WIRE002@src/frob/gates/_tdd_order.py, unknown-argument@tests/unit/test_app_runners_process.py, unknown-argument@tests/unit/test_pytest_spawn_env_wiring.py
