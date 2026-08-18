## Done report

Same shape as T-2326 (dropped this session): the single claimed (rule,
file) identity is malformed -- both rule id and file path are blank in
the ticket body's "New (rule, file) identit(ies) filed here:" list, and
the ticket's own count states 0 actual finding(s) across that 1 identity.
Nothing to reproduce or fix. Confirmed by reading `frob ticket show
T-2332` directly: scope is empty ([]), rule/file fields are empty
strings.

Entirely stale (never a real finding), not a case of pre-existing work
folded elsewhere.

### Changed
```
 tickets/T-2332/ticket.md | 2 +-
 1 file changed, 1 insertion(+), 1 deletion(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@scripts/fleet_status.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/release/_cli.py, COV001@scripts/fleet_status.py, COV001@src/frob/tickets/_land_git_ops.py, COV001@src/frob/tickets/_leases.py, COV001@src/frob/verify/_drain.py, COV001@src/frob/verify/_quarantine.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, DOC001@docs/commands/release.md, DOC002@scripts/fleet_status.py, DOC002@src/frob/app/verify_runner.py, DOC002@src/frob/verify/_drain.py, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT002@src/frob/verify/_drain.py, DRIFT002@tests/system/test_frob_self_model.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2332/src/frob/verify/_worker.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_new.py, PRE001@tickets/T-2332, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/tickets/_leases.py, TICK004@tickets.md, WIRE003@docs/modules/cli.md, unresolved-import@src/frob/arch/_abstraction.py, unresolved-import@src/frob/graph/_core.py, unresolved-import@tests/test_arch_near_duplicate_native.py, unresolved-import@tests/unit/strata/test_capacity.py, unresolved-import@tests/unit/test_arch_python_native.py, unresolved-import@tests/unit/test_capability_native.py, unresolved-import@tests/unit/test_dup_core.py, unresolved-import@tests/unit/test_extract_native.py, unresolved-import@tests/unit/test_lang_strata.py
