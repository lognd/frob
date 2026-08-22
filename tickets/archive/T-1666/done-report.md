## Done report

(v3, evidence bound)

Changed: none (investigation-only; no waiver added/removed/rewritten,
0 source files touched).

Findings:
- OPAQUE001 (the 142 findings this ticket was filed to classify):
  already resolved on main by T-1668 (landed) plus the 5-site
  _config_external.py re-waive it called for. Confirmed via
  `frob check --ticket T-1666 --json`: gate:OPAQUE exit_code=0, 29
  diagnostics, all note-severity (waived). 0 errors. Nothing left to
  classify or re-waive.
- PERF001-014: confirmed NOT the same bug shape -- `Violation.symref`'s
  docstring in src/frob/gates/_models.py explicitly designates PERF as
  intentionally file-scoped, alongside TEST005/TEST006. The bound
  evidence test directly exercises this exact symref-less (file-scope)
  matching path in `_match_waiver`. No fix needed.
- SEC005 (src/frob/gates/_taint_gate.py): measured 0 live violations
  repo-wide via a direct call to `taint_gate(Path("."))`. No exposure.
- PII010/011/012 (src/frob/gates/_pii_structural/*.py): genuine dormant
  missing-symref hole, same shape as CACHE001's. 93 raw violations, 21
  (rule, file) pairs carry 2+ under file-scope-only match, but only 1
  finding is currently UNWAIVED (PII012 at tests/test_capability_
  registry.py:902, unrelated pre-existing finding, not touched). Real
  fix filed as its own successor (T-2696, renumbers on land).

Evidence: tests/test_gates.py::TestTestGate::
test_match_waiver_prefix_reach_gated_to_package_scoped_rules -- an
EXISTING, unmodified test that directly exercises `_match_waiver`'s
symref-less/file-scope matching path, the exact mechanism this
ticket's PERF/PII findings turn on. Not a repro (no bug fixed here);
cited as the mechanism-level demonstration backing the classification,
per `--no-behavior-change`'s own posture (a real behavioral claim,
verified, just not a NEW behavior).

Gates: frob check --ticket T-1666 --json -> 58 error(s) total
repo-wide, ALL pre-existing baseline unrelated to this ticket (0 files
changed here); gate:OPAQUE (this ticket's own subject) is 0 error(s) /
29 note(s), confirmed unaffected by this ticket's merge.

Filed: T-2696 (renumbers at land) -- "Populate PII010/011/012
symref (dormant over-forgiveness hole, T-1666 successor)".

### Changed
```
 rapid-debt.jsonl                   |  5 +++
 src/frob/app/check_runner.py       | 13 ++++++
 src/frob/app/sys_runner.py         | 14 ++++++
 tickets/T-1656/done-report.md      | 68 ++++++++++++++++++++++++++++
 tickets/T-1656/ticket.md           | 56 +++++++++++++++++++++++-
 tickets/T-1666/done-report.md      | 64 +++++++++++++++++++++++++++
 tickets/T-1666/ticket.md           | 90 +++++++++++++++++++++++++++++++++++++-
 tickets/T-2694/ticket.md | 72 ++++++++++++++++++++++++++++++
 tickets/T-2695/ticket.md | 62 ++++++++++++++++++++++++++
 tickets/T-2696/ticket.md | 70 +++++++++++++++++++++++++++++
 10 files changed, 511 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestTestGate::test_match_waiver_prefix_reach_gated_to_package_scoped_rules` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 34 error(s), 1842 warning(s), 699 waived
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC002@src/frob/gates/_milestone.py, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, RENDER001@src/frob/release/_cli.py, SEC004@tests/test_tickets_organization.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
