## Done report

Deliberate, reviewed SELFAUDIT001 fix for the parent T-2303 sweep's
capability-declaration findings.

design/frob.strata: added tests/unit/test_land_sibling_regression.py to
the testsuite node's may "fs.read" via-list (read_text() on a v2 tmp-repo
test fixture path, line 275) and tests/unit/test_new_ticket_scope_
overlap_warning.py to the may "fs.write" via-list (write_text() in the
file's own private _write() test-fixture helper, line 24). Both reviewed
individually: genuine, needed effects on isolated tmp/test-fixture paths,
not production repo mutation -- declared, not restructured, matching
every other test-fixture entry already in these same via-lists.

Re-measured undeclared-effect count before starting per the ticket's own
instruction: still exactly the 2 originally scoped, plus 5 more in
tests/unit/verify/test_watermark.py (unrelated, out of this ticket's
declared scope) -- filed as T-2343 residue rather than expanding scope
mid-ticket.

docs/design/registry/capability-via-ratchet.lock.json: bumped 3 entries,
each individually reviewed, not blindly synced:
- core::fs.write 21->22: git log -S confirmed the 22nd via-list site
  (src/frob/scaffold/_skills_sync.py) was added by an already-landed,
  already-reviewed commit (1e460771a) -- the ratchet's own accepted_count
  had simply not caught up. Catching up a stale ceiling to an
  already-approved grant is not approving new scope.
- testsuite::fs.read 130->131 and testsuite::fs.write 327->328: direct,
  attributable consequence of this ticket's own two new via-list entries
  above -- one site each.
No other ratchet entries touched.

Verified: tests/unit/test_land_sibling_regression.py tests/unit/test_new_ticket_scope_overlap_warning.py
-- 10 passed. `frob check --only sys`: zero SYS111 findings (was 3:
core::fs.write, testsuite::fs.read, testsuite::fs.write). `frob check
--only gates-security --ticket T-2323`: zero SELFAUDIT001 findings.

Filed: T-2343 (test_watermark.py's 5 undeclared effects, deliberately
out of this ticket's scope).

### Changed
```
 tickets/T-2323/ticket.md | 5 ++++-
 1 file changed, 4 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_land_sibling_regression.py::TestSiblingStateRegressionGuard::test_pre_fix_shape_would_have_silently_reverted_sibling` (pytest node id, verified passing when recorded)
- `tests/unit/test_new_ticket_scope_overlap_warning.py::TestScopeOverlapWarnings::test_real_case_four_prior_tickets_all_named` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@scripts/fleet_status.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/release/_cli.py, COV001@scripts/fleet_status.py, COV001@src/frob/tickets/_land_git_ops.py, COV001@src/frob/tickets/_leases.py, COV001@src/frob/verify/_drain.py, COV001@src/frob/verify/_quarantine.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, DOC001@docs/commands/release.md, DOC002@scripts/fleet_status.py, DOC002@src/frob/app/verify_runner.py, DOC002@src/frob/verify/_drain.py, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT002@src/frob/verify/_drain.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2323/src/frob/verify/_worker.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PERF004@src/frob/app/ticket_runner/_new.py, PRE001@tickets/T-2323, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/tickets/_leases.py, TICK004@tickets.md, WIRE003@docs/modules/cli.md
