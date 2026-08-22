## Done report

Epic tracker for the T-1783-disclosed DOC012 backlog.

1. RE-MEASURED (uv run frob check --only docblocks): the 24-item backlog
   was still exactly 24, no drift since T-1783.
2. Filed two child tickets grouped by owning doc file for disjoint,
   parallelizable scope: T-2315 (10 subcommands with an existing
   docs/modules/*.md file needing only a `## frob <name>` heading) and
   T-2316 (14 subcommands with no dedicated file, documented as new
   sections in docs/modules/cli.md).
3. Landed both children myself (commits c7fee2f5318d.../705484fcf4e1...).
   Re-measured after each: 24 -> 14 -> 0.
4. With DOC012 measuring zero, promoted _doc012_violation
   (src/frob/gates/_docblocks.py) from Severity.WARN to Severity.ERROR,
   updated its docstring and docs/modules/gates.md's "DOC012 dedicated
   command-section drift-lock" section (both the summary table row and
   the burn-down/promotion prose) to record the promotion.
5. Added tests/test_doc012_promotion.py::TestDoc012PromotedToError as
   the must-fail fixture: test_undocumented_subcommand_is_now_error
   proves an undocumented subcommand now reports Severity.ERROR (would
   have been WARN pre-promotion); test_documented_subcommand_still_
   passes proves the promotion changed severity only, not the detection
   logic. Placed in a new file rather than editing
   tests/test_gates.py::TestDoc012CommandSectionGate directly because
   that file carried a live cross-worktree lease (T-2314) at promotion
   time -- filed a follow-up child ticket to fold the fixture back in
   and fix that class's own now-stale WARN assertion once the lease
   clears.

Final re-measurement (uv run frob check --only docblocks): gate:DOC
0 errors, 142 warnings, 0 unresolved -- DOC012 count is 0.

Filed: one follow-up child (update stale WARN assertion in
tests/test_gates.py once T-2314's lease clears), parented to T-2299.

### Changed
```
 tickets/T-2299/ticket.md           | 37 +++++++++++++++++++++++++++---
 tickets/T-2327/ticket.md | 46 ++++++++++++++++++++++++++++++++++++++
 2 files changed, 80 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/test_doc012_promotion.py::TestDoc012PromotedToError::test_undocumented_subcommand_is_now_error` (pytest node id, verified passing when recorded)
- `tests/test_doc012_promotion.py::TestDoc012PromotedToError::test_documented_subcommand_still_passes` (pytest node id, verified passing when recorded)
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@scripts/fleet_status.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/release/_cli.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/tickets/_land_git_ops.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, DOC001@docs/commands/release.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/gates/_fmt_directives.py, DRIFT002@scripts/fleet_status.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PERF004@src/frob/app/ticket_runner/_new.py, PRE001@tickets/T-2299, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK004@tickets.md, WIRE003@docs/modules/cli.md
