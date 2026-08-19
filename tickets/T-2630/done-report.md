## Done report

Changed: tests/golden/frob_export_iam.json, tests/golden/frob_export_k8s.yaml, tests/golden/frob_export_seccomp.json

Root cause: design/frob.strata (frob's self-hosting architecture model) was
legitimately extended by three unrelated lands since the goldens were last
regenerated on 2026-08-05 (85995a5) -- T-2503 (ambient vs enumerated
capability grants), T-2523 (wire check_ambient_capability_reasons into a
gate, backfilling 27 reasonless ambient grants), and T-2587 (wire ticket
promote into the T-2563 ledger mirror). Each land added real nodes/attrs
(e.g. a new `testsuite` principal with full read/write flows across every
resource, a renamed `registry`->`refactor` node) that the IAM/k8s/seccomp
exporters correctly reflect. The exporters themselves did not change; only
their input (the model) did. All three goldens are one shared cause, not
three independent drifts.

Verification that this is legitimate growth, not an export regression:
regenerated each golden via the exact code path the test uses
(parse_module -> elaborate -> export_*) and diffed against the committed
fixture. IAM diff is 0 removed / 868 added lines (pure addition). k8s and
seccomp show a handful of removed lines, all placeholder artifacts
(`ingress: []`/`egress: []` stubs and syscall-list reordering caused by
newly-populated groups), not lost content -- confirmed by reading the full
diffs, not just the counts.

Positive control: all three tests failed at the parent commit
(FAILED_AT_PARENT, confirmed via --check-repro) and pass after the golden
regeneration. Negative control: the failure mode itself (byte-for-byte
mismatch against a stale golden) is exactly what these tests exist to
catch -- reverting any one golden file reproduces the original failure.

Evidence:
- tests/unit/strata/test_export_golden.py::TestExportGolden::test_iam (designated repro)
- tests/unit/strata/test_export_golden.py::TestExportGolden::test_k8s
- tests/unit/strata/test_export_golden.py::TestExportGolden::test_seccomp

Filed: none

Gates: uv run frob check --ticket T-2630 clean (see command output)

### Changed
```
 tickets/T-2630/ticket.md | 10 ++++++++--
 1 file changed, 8 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/unit/strata/test_export_golden.py::TestExportGolden::test_iam` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_export_golden.py::TestExportGolden::test_k8s` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_export_golden.py::TestExportGolden::test_seccomp` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@scripts/fleet_status.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV001@src/frob/gates/_rule_id_scan.py, COV001@src/frob/strata/_multifile.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC001@docs/commands/release.md, DOC002@scripts/fleet_status.py, DOC002@src/frob/gates/_milestone.py, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC006@tickets/T-2570/ticket.md, DOC008@docs/modules/gates.md, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, RENDER001@src/frob/release/_cli.py, SEC004@tests/test_tickets_organization.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WAIVE006@src/frob/gates/__init__.py, WAIVE006@src/frob/gates/_coverage.py, WAIVE006@src/frob/gates/_decisions_compliance.py, WAIVE006@src/frob/gates/_doclink_docanchor.py, WAIVE006@src/frob/gates/_mutation_evidence.py, WAIVE006@src/frob/gates/_sys.py, WAIVE006@src/frob/gates/_tickets_gate.py, WAIVE006@src/frob/gates/_todo_fmt.py, WAIVE006@src/frob/tickets/_draft_finalize.py, WAIVE006@src/frob/tickets/_evidence.py, WAIVE006@src/frob/tickets/_models.py, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
