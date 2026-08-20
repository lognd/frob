## Done report

Changed:
src/frob/gates/_doclink_docanchor.py::_resolve_relative_link (new)
src/frob/gates/_doclink_docanchor.py::_crawl_reachable (site 1, was line 141)
src/frob/gates/_doclink_docanchor.py::_doc008_scan_doc (site 2, was line 271)

Evidence:
tests/test_gates.py::TestDoclinkGate::test_valid_parent_relative_link_with_two_dotdots_resolves
tests/test_gates.py::TestDoclinkGate::test_genuinely_missing_target_still_fires_doc008_after_dotdot_fix
tests/test_gates.py::TestDoclinkGate::test_dotdot_link_escaping_above_repo_root_is_refused
tests/test_gates.py::TestDoclinkGate::test_broken_relative_link_target_fires_doc008 (pre-existing,
re-run to confirm no regression)

Validated against the real consumer repo (/home/logan/projects/aprog-public,
read-only): `frob check --only doclink` there now reports 0 errors (was
DOC008 firing on all 10 reported false-positive parent-relative links
before this fix). The report's cited genuine-miss case
(docs/grader/overview.md:143-146) no longer contains any relative markdown
links at HEAD in that repo (only http(s) links remain there now) -- could
not be reproduced as a live positive control against current consumer
HEAD; the genuinely-missing-target and escape-above-root behavior is
instead covered directly by the two new regression tests above, which
plant and assert both cases explicitly.

Filed: none

Gates: `frob check --ticket T-2704` gate:DOC family scoped diff-driven
checks pass; repo-wide gate counts include pre-existing unrelated findings
(see gate:scope-note in check output -- unscoped families are not this
ticket's responsibility).

### Changed
```
 src/frob/gates/_doclink_docanchor.py | 43 +++++++++++++++++++++--
 tests/test_gates.py                  | 67 ++++++++++++++++++++++++++++++++++++
 tickets/T-2704/ticket.md             | 21 ++++++++++-
 3 files changed, 127 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestDoclinkGate::test_valid_parent_relative_link_with_two_dotdots_resolves` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestDoclinkGate::test_genuinely_missing_target_still_fires_doc008_after_dotdot_fix` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestDoclinkGate::test_dotdot_link_escaping_above_repo_root_is_refused` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestDoclinkGate::test_broken_relative_link_target_fires_doc008` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 47 error(s), 1534 warning(s), 680 waived
- error-findings: ARCH001@src/frob/gates/_doclink_docanchor.py, ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC002@src/frob/gates/_milestone.py, DOC006@tickets/T-2691/ticket.md, DOC006@tickets/T-2703/ticket.md, DOC006@tickets/T-2704/ticket.md, DOC006@tickets/T-2705/ticket.md, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII010@src/frob/deploy/_audit.py, PII012@src/frob/doctor.py, PII012@src/frob/serve/_socketd.py, PII012@tests/system/test_cli_doctor.py, PII012@tests/test_capability_registry.py, PII012@tests/test_doctor.py, PII012@tests/test_hook_diagnosis_nudge.py, PII012@tests/test_prework_parity.py, PII012@tests/test_vet.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-2704, RENDER001@src/frob/release/_cli.py, SEC004@tests/test_tickets_organization.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
