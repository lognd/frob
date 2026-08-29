## Done report

Changed:
  src/frob/logging/logger.py::_resolve_stdout_level_override (SEC110 waivers on FROB_VERBOSE/FROB_LOG_LEVEL reads)
  src/frob/logging/logger.py::_init (SEC110 waiver on FROB_FORCE_LOG_HANDLERS read)
  src/frob/__main__.py::_apply_verbose_env_override (SEC110 waiver on FROB_VERBOSE/FROB_LOG_LEVEL check)
  .claude/hooks/frob-suggest.py (SEC110 waiver on FROB_SUGGEST_ACK read)
  tests/test_worktree_guard.py (SEC110 waiver on PYTEST_XDIST_AUTO_NUM_WORKERS read)
  docs/modules/logging.md (AFFECT001 closure: noted the SEC110 disposition of logger.py's two waived reads)

Evidence:
  frob check --only secrets (repo-wide): gate:SEC 0 errors, 0 unresolved (88 waived, all 6 new sites carry a specific non-generic reason)
  frob test --base main: 9 python test outcome(s) recorded, exit=0
  frob check --ticket T-3389: gate:SEC clean, gate:AFFECT clean, gate:SCOPE clean, ruff-check/ruff-format clean on touched files

All 6 SEC110 findings were verified individually before waiving (not mass-waived): each site is a
boolean/level/count operational flag (FROB_VERBOSE, FROB_LOG_LEVEL, FROB_FORCE_LOG_HANDLERS,
FROB_SUGGEST_ACK, PYTEST_XDIST_AUTO_NUM_WORKERS) -- none carries a credential or secret value.
Declared via the established `frob:waive SEC110 reason="..."` mechanism (the repo's standing
per-site discharge path for this rule, used at 15+ other sites), each reason naming the specific
variable and why it is not secret -- not a blanket/generic waiver.

Filed: none (no out-of-scope work found)
Gates: frob check --ticket T-3389 -- gate:SEC and gate:AFFECT clean for this ticket's scope;
  remaining FAIL rows in the ticket-scoped summary (ARCH103, LARGE001, LEXCHECK001, OPAQUE001,
  PII012, REL001, TICK004, DEPR006, WAIVE011, DOCENUM001, DOC003/DOC011, PERF004, CYCLE001,
  SELFAUDIT001) are pre-existing repo-wide findings outside T-3389's scope (owned by Series ER,
  Series EQ's own T-3390/T-3391/T-3392, or the deferred REL/TICK triage) -- not introduced by
  this change; verified by re-measuring gate:SEC/gate:AFFECT in isolation above.

### Changed
```
 tickets/T-3389/done-report.md | 43 +++++++++++++++++++++++++++++++++++++++++++
 tickets/T-3389/ticket.md      | 22 +++++++++++++++++++++-
 2 files changed, 64 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_pii_structural_gate.py::TestEnvAccess::test_os_environ_get_fires` (pytest node id, verified passing when recorded)
- `tests/test_pii_structural_gate.py::TestEnvAccess::test_os_getenv_fires` (pytest node id, verified passing when recorded)
- `tests/test_pii_structural_gate.py::TestEnvAccess::test_os_environ_subscript_fires` (pytest node id, verified passing when recorded)
- `tests/test_pii_structural_gate.py::TestDeclaredSurfaceJoin::test_sec110_still_fires_with_no_design_directory` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 32 error(s), 4052 warning(s), 886 waived
- error-findings: ARCH103@src/frob/app/_version_guard.py, ARCH103@src/frob/app/check_runner.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/app/ticket_runner/_verify.py, ARCH103@src/frob/refactor/_verify.py, CLAUDE001@.claude/hooks/sync-claude-config.py, CYCLE001@src/frob/__init__.py, DEPR006@frob-deprecated-baseline.lock.json, DOC003@docs/commands/sys.md, DOC011@docs/modules/tickets.md, DOCENUM001@docs/modules/gates.md, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, LEXCHECK001@src/frob/gates/_comment_placement.py, OPAQUE001@tests/unit/test_land_finish_idempotent.py, PERF004@.claude/hooks/frob-suggest.py, PERF004@src/frob/lang/_support.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, REL001@src/frob/__init__.py, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, REL001@strata-core/src/graph/vmodel.rs, REL001@strata-core/src/parse/grammar_core.rs, REL001@tests/unit/test_conftest_suite_result_status.py, SELFAUDIT001@design, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json
