## Done report

Investigated why 8 SCOPE002 findings against
docs/modules/tickets.md#coalescing-verify-worker-t-1688's `frob:describes`
targets in src/frob/verify/_worker.py were reported as ERROR-severity
while every other SCOPE002 finding against the same doc file is WARNING.

Result: NOT REPRODUCIBLE against the current tree. Live-reproduced T-1973
(the exact ticket cited in the bug report, scope=['docs/modules/
tickets.md'] verbatim, state=done, made zero content edits) via
`frob check --ticket T-1973 --only scope --only prework --json`:

- 106 SCOPE002 findings total, ALL severity=warning (0 error).
- Zero findings mention `_worker.py` or "coalescing" at all -- the
  `doc_missing_code` gap this bug report describes does not fire for
  docs/modules/tickets.md against `_worker.py` any more, in either
  severity.

Root cause of why it no longer fires: `_worker.py`'s `frob:doc` directives
all point to `docs/modules/tickets-verify-sweep.md#coalescing-verify-
worker-t-1688` (verified: `git grep` shows all 8 occurrences use that
path, not `docs/modules/tickets.md`), and `docs/modules/tickets.md` no
longer carries any `frob:describes`/heading for that anchor (verified:
grepped for "1688", "_worker", "verify-worker" in
docs/modules/tickets.md -- zero hits). This is exactly the same doc-
family split T-2311 is chartered to clean up (docs/modules/tickets.md
splitting into docs/modules/tickets-*.md, T-2135's own residue) -- the
`_worker.py` doc target already moved to `tickets-verify-sweep.md`
sometime between when T-2128 was filed and now, which independently
removed the doc_missing_code edge this bug depended on.

Also confirmed by direct code read that no severity-promotion path for
SCOPE002 exists in the current source: `_scope002_violation`
(src/frob/gates/__init__.py) hardcodes `severity=Severity.WARN`
unconditionally for every SCOPE002 finding it builds, and `frob.toml`
carries no `[gates.severity]` entry for SCOPE002 (`_apply_severity_
overrides` in src/frob/gates/_waive.py is the only other severity-
mutation path, and it is rule-id-keyed -- it would flip ALL SCOPE002
findings together, never a subset of 8 against one anchor). No dangling
mechanism was found that could still promote a subset of SCOPE002
findings to ERROR today.

Conclusion: the specific defect T-2128 reported is gone, most likely
resolved as a side effect of other tickets in this same contended
tickets.md-adjacent family (T-2135/its siblings) moving the `_worker.py`
doc target out from under `docs/modules/tickets.md` before this ticket
was picked up. No code change made -- there is nothing left to fix, and
forcing a change here risks stepping on T-2311's own declared scope over
the same file family. Re-open if the ERROR-severity shape is seen again
against a different anchor; if so, it will need a live repro with the
current gate JSON output attached, since this write-up could not find
one.

Changed: none (investigation-only; symptom no longer reproduces)
Evidence: tests/test_gates.py::TestScope002ClosureGate::test_silent_on_closed_scope

### Changed
```
 rapid-debt.jsonl              |  1 +
 tickets/T-2128/ticket.md      | 22 ++++++++++-
 tickets/T-2134/done-report.md | 63 +++++++++++++++++++++++++++++
 tickets/T-2134/ticket.md      | 26 +++++++++++-
 tickets/T-2684/ticket.md      | 92 +++++++++++++++++++++++++++++++++++++++++++
 5 files changed, 200 insertions(+), 4 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 38 error(s), 971 warning(s), 697 waived
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC002@src/frob/gates/_milestone.py, DOC006@tickets/T-2684/ticket.md, DOC008@docs/modules/gates.md, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, RENDER001@src/frob/release/_cli.py, SEC004@tests/test_tickets_organization.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
