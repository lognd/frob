## Done report

Changed: src/frob/__init__.py, src/frob/arch/__init__.py, src/frob/lang/__init__.py, src/frob/scaffold/__init__.py, src/frob/testing/__init__.py

Root cause: genuine export gap, NOT a stale test/baseline. 12 public
symbols across 5 packages were real, cross-module-referenced public API
that had never been re-exported through their package's __init__.py:

- src/frob/repo_meta.py: load_arch_config, stale_install_warning,
  declared_min_frob_version, stale_binary_warning -- each already carries
  frob:doc/frob:tests at its definition, imported by app/config.py,
  app/ticket_runner/_land_cmd.py, check/_python.py, gates/_arch.py.
- src/frob/arch/_normalized.py::caught_type_names -- frob:doc
  docs/modules/arch.md#normalized-code-model, used by _mayraise.py and
  gates/_exhaustive_handling.py.
- src/frob/lang/_support.py: derive_capability_registry,
  capability_conformance_violations, CapabilityRequirement,
  CapabilityStatus, AdapterCapabilitySupport -- the T-2365 adapter
  capability contract, frob:doc docs/modules/lang.md#adapter-capability-
  contract-t-2365, consumed by gates/_lang_conformance.py.
- src/frob/scaffold/_skills_sync.py: sync_skills, SkillsSyncReport --
  frob:doc docs/commands/sync-skills.md#public-api, consumed via
  _cli_parsers.
- src/frob/testing/_coverage_refresh.py::pytest_load_initial_conftests --
  a pytest11 entry-point hook registered directly against this module in
  pyproject.toml (not via __init__.py, so exporting it cannot cause
  double-registration), already carries frob:doc docs/modules/testing.md
  #public-api.

Every one of the 12 was checked against the "genuinely public vs.
accidental cross-module import" bar before being exported: all 12 already
carried frob:doc + frob:tests directives at their own definition and real
cross-module callers found via git grep -- none were accidental, none
were demoted to private, the list did not shrink.

T-2630/T-2635 do NOT share a root cause: T-2630 was stale generated
fixtures against an intentionally-evolving design model; T-2635 is
missing __init__.py re-exports for already-deliberate public symbols --
unrelated mechanisms, confirmed by inspecting both independently before
touching either.

Cycle safety: re-exporting into a package __init__.py can create an
import cycle. Ran `frob check --only cycle` after the change: exactly 2
errors, one is claude-config-drift (pre-existing, unrelated), the other
is the SAME 160-node SCC src/frob/__init__.py's own header comment
already documents as a live, undischarged T-2363/T-2583 finding.
src/frob/repo_meta.py -- the only new import added to src/frob/__init__.py
-- imports nothing but frob.logging, so it cannot be a new participant in
that SCC. No second cycle was introduced.

Positive control: test_all_nine_packages_report_zero_missing_symbols
fails at the parent commit (FAILED_AT_PARENT, confirmed via --check-repro)
and passes after the 5 __init__.py edits. Negative control: this is
exactly the failure mode the test exists to catch (a genuinely
un-exported public symbol reads as a real offender in its assertion) --
reverting any one of the 5 files reproduces the original failure.

Scope was broadened from the ticket's original tests/unit/test_exports.py
to add the 5 __init__.py files via `frob ticket scope --add`, since the
real fix required touching production code, not the test.

Evidence: tests/unit/test_exports.py::TestFrobExportsPolicyResidue.test_all_nine_packages_report_zero_missing_symbols (designated repro)

Filed: none

Gates: uv run frob check --ticket T-2635 -- repo-wide families (per
gate:scope-note) show pre-existing failures unrelated to this change
(SEC/PII/PERF/TICK/WAIVE/etc, matching the same repo-wide baseline seen
on T-2630); frob-cycle shows only the pre-existing T-2363 SCC, no new
cycle. frob-exports(src/frob/*) all pass or show unrelated pre-existing
counts for other packages outside this ticket's scope.

### Changed
```
 src/frob/__init__.py          | 10 +++++
 src/frob/arch/__init__.py     |  2 +
 src/frob/lang/__init__.py     | 10 +++++
 src/frob/scaffold/__init__.py |  3 ++
 src/frob/testing/__init__.py  |  2 +
 tickets/T-2635/ticket.md      | 99 ++++++++++++++++++++++++++++++++++++++++++-
 6 files changed, 124 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/unit/test_exports.py::TestFrobExportsPolicyResidue::test_all_nine_packages_report_zero_missing_symbols` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV001@src/frob/gates/_rule_id_scan.py, COV001@src/frob/strata/_multifile.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_milestone.py, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC006@tickets/T-2570/ticket.md, DOC008@docs/modules/gates.md, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, PRE001@tickets/T-2635, RENDER001@src/frob/release/_cli.py, SEC004@tests/test_tickets_organization.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WAIVE006@src/frob/gates/__init__.py, WAIVE006@src/frob/gates/_coverage.py, WAIVE006@src/frob/gates/_decisions_compliance.py, WAIVE006@src/frob/gates/_doclink_docanchor.py, WAIVE006@src/frob/gates/_mutation_evidence.py, WAIVE006@src/frob/gates/_sys.py, WAIVE006@src/frob/gates/_tickets_gate.py, WAIVE006@src/frob/gates/_todo_fmt.py, WAIVE006@src/frob/tickets/_draft_finalize.py, WAIVE006@src/frob/tickets/_evidence.py, WAIVE006@src/frob/tickets/_models.py, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
