## Done report

-- batch 2 (DOC001/DOC005)

Continuation ticket of T-2653 (which closed on landing its own batch
1). This batch clears 2 of the 37 remaining tracked identities.

### Cleared this batch

- DOC001 docs/commands/release.md -- was linked from nowhere; added it
  to docs/index.md's docs/commands table, the same pattern every
  sibling command doc already uses (scaffold.md, cycle.md, outline.md,
  etc. are all listed there; release.md was simply missing).
- DOC005 docs/modules/cli.md -- generated command table was stale
  relative to the live argparse registry; regenerated via `frob docs
  --sync-commands` (the exact remedy the gate's own message names).

### Verification

Before: `frob check --only doclink --json` (captured in T-2653's own
earlier triage, /tmp/full_check.json) showed both as ERROR.
After: identical scoped check shows ZERO DOC001/DOC005 findings for
either file.

Purely additive/regenerated doc content, no code touched -- covered by
`frob:no-behavior-change` (inherited from this ticket's own body).
No dedicated pytest surface for either fix (a docs table row and a
regenerated block); per playbook section 5's docs-only precedent,
binding the existing CLI-dispatch integration test as evidence.

### Evidence

- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches

### Count against the 37

2 of 37 cleared this batch (DOC001, DOC005). 35 remain tracked; will
be carried into a further follow-up ticket since this land closes this
one too.

### Changed
```
 docs/index.md                           |  1 +
 docs/modules/cli.md                     |  2 +-
 tickets/T-2674/done-report.md | 53 +++++++++++++++++++++++++++++++++
 tickets/T-2674/ticket.md      |  4 +++
 4 files changed, 59 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 38 error(s), 1642 warning(s), 697 waived
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC002@src/frob/gates/_milestone.py, DOC006@tickets/T-2570/ticket.md, DOC008@docs/modules/gates.md, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, PRE001@tickets/T-2674, RENDER001@src/frob/release/_cli.py, SEC004@tests/test_tickets_organization.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
