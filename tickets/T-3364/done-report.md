## Done report

Measured `frob check --only release --only registry --only refs` on
main: gate:REF 3 errors, all REF002 ("exactly one inbound reference --
a single point of anchor is fragile") on docs/modules/ci_report.md,
ci_validity.md, ghio.md.

Each doc genuinely, permanently documents exactly one small, single-
purpose support module (ci_report.py's pytest-output parsing,
ci_validity.py's test-outcome-vs-affects-graph classification, ghio.py's
one gh CLI subprocess seam) -- inventing a second consumer/declaration
to satisfy REF002 would be manufactured busywork, not a genuine fix.
Added `<!-- frob:waive REF002 reason="..." -->` to each, matching the
existing "deliberately singly-anchored, a second consumer would not be
genuine" precedent already used for docs/audits/branch-stranded-work-
2026-08-25.md, docs/design/test005-ratchet-schedule.md, and others.

Re-measured: gate:REF 3 -> 0.

Split out of a wider draft (gate:REG002's `_waive.py` fix) because that
file carries a live in-progress lease from T-3295 (an unrelated feature
actively reworking the same frozenset region) -- landing REG002's fix
now would risk a conflict with T-3295's own in-flight work. REG002 is
reported separately as still-pending, to be landed once T-3295 releases
the file.

Filed as a draft off T-3343 (measurement-first triage ticket for the
wider gate:COV/TICK/REL/REG/REF sprint assignment); mints a real id at
land/renumber.

### Changed
```
 docs/modules/ci_report.md               |  2 ++
 docs/modules/ci_validity.md             |  2 ++
 docs/modules/ghio.md                    |  2 ++
 tickets/T-3227/done-report.md           |  2 +-
 tickets/T-3236/done-report.md           |  2 +-
 tickets/T-3238/done-report.md           |  2 +-
 tickets/T-3363/done-report.md           | 58 ++++++++++++++++++++++++++++++++
 tickets/T-3363/ticket.md                | 56 +++++++++++++++++++++++++++++++
 tickets/T-3364/ticket.md                |  9 +++++
 tickets/T-draft-547b0587/done-report.md | 46 +++++++++++++++++++++++++
 tickets/T-draft-547b0587/ticket.md      | 59 +++++++++++++++++++++++++++++++++
 tickets/archive/T-2978/done-report.md   |  3 +-
 tickets/archive/T-3031/done-report.md   |  9 +++--
 13 files changed, 245 insertions(+), 7 deletions(-)
```

### Evidence
- `tests/test_refs_gate.py::TestMarkdownWaive::test_ref002_on_md_doc_suppressed_by_inline_waive` (pytest node id, verified passing when recorded)
- `tests/test_refs_gate.py::TestMarkdownWaive::test_ref002_on_md_doc_without_waive_still_fires` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 44 error(s), 3942 warning(s), 880 waived
- error-findings: ARCH103@src/frob/app/_version_guard.py, ARCH103@src/frob/app/check_runner.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/refactor/_verify.py, CLAUDE001@.claude/hooks/sync-claude-config.py, CYCLE001@src/frob/__init__.py, DEPR006@frob-deprecated-baseline.lock.json, DOC002@src/frob/tickets/_leases.py, DOC004@docs/commands/check.md, DOC005@docs/modules/cli.md, DOC007@src/frob/app/check_runner.py, DOC011@docs/guides/release.md, DOC011@docs/modules/tickets.md, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, DRIFT002@src/frob/app/check_runner.py, FLAGCOV001@frob.toml, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, LEXCHECK001@src/frob/gates/_comment_placement.py, OPAQUE001@tests/unit/test_land_finish_idempotent.py, PERF004@.claude/hooks/frob-suggest.py, PERF004@src/frob/lang/_support.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-3364, REG002@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, REL001@strata-core/src/graph/vmodel.rs, REL001@strata-core/src/parse/grammar_core.rs, REL001@tests/unit/test_conftest_suite_result_status.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/test_worktree_guard.py, SELFAUDIT001@design, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json, WIRE002@src/frob/gates/_tdd_order.py, WIRE002@tests/conftest.py
