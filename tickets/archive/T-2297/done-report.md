## Done report

frob:no-behavior-change reason="pure formatting (E402 noqa annotations matching this file's own existing guard-import pattern, E501 line-wrap) and an unused-variable removal in a test; no behavior changed"

Re-measured the sweep's 6 claimed (rule, file) identities against the
current tree.

Genuine and fixed:
- E402 scripts/fleet_status.py -- module-level imports below the
  sys.path/require_python() guard at the top of the file are intentional
  (must run before anything else can import), matching the file's own
  existing `# noqa: E402` on the `_require_python` import 2 lines above;
  added the same annotation to every import in that block (lines 35-44,
  not just the 3 the sweep happened to cite -- `frob check --only lint`
  showed all 10 flagged, not just the subset in the ticket body).
- E501 scripts/fleet_status.py:1326 -- wrapped the over-long f-string.
- F841 tests/test_ticket_land.py:1483 -- `ticket = _seed_v2_ticket(...)`
  assigned a value never read; dropped the assignment.

Already resolved before this ticket started (shared files, landed by
T-2260/T-2206 earlier in this same batch):
- E501 src/frob/lang/_nodes.py -- fixed by T-2260's land.
- F541 tests/test_ticket_work_and_land_finish.py -- fixed by T-2260's land.

Not fixed, flagged as a sweep-tooling defect rather than a code finding:
- The first identity in T-2297's list rendered as a blank rule id (`-   `
  with no rule name, file, or message) -- garbled/empty, not a real
  (rule, file) identity to fix. Not re-filing a separate ticket for this
  given the session's remaining budget; noting it here so it is not
  silently dropped. Worth a follow-up on the rapid-sweep ticket-filing
  path (src/frob/app/ticket_runner/_rapid_sweep.py) if it recurs.

Changed: scripts/fleet_status.py (noqa annotations + line-wrap, no behavior
change), tests/test_ticket_land.py (removed unused local, no behavior
change)

Evidence: tests/test_ticket_land.py::TestRecordLandCommit::test_record_land_commit_never_absorbs_a_bystanders_dirty_file
(passes)

Filed: none (the one non-code finding -- the garbled blank identity -- is
recorded above rather than filed, per this session's remaining budget;
flag it if it recurs)

Gates: `frob check --only lint` confirms 0 findings for scripts/fleet_status.py,
src/frob/lang/_nodes.py, tests/test_ticket_land.py after this change.

Claimed vs genuinely-new: 6 claimed identities, 4 genuinely reproduced (3
fixed here, 1 -- the blank entry -- unresolvable as a code fix), 2 already
resolved by an earlier ticket in this same sweep batch (T-2260).

### Changed
```
 scripts/fleet_status.py   | 25 ++++++++++++++-----------
 tests/test_ticket_land.py |  2 +-
 tickets/T-2297/ticket.md  |  6 +++++-
 3 files changed, 20 insertions(+), 13 deletions(-)
```

### Evidence
- `tests/test_ticket_land.py::TestRecordLandCommit::test_record_land_commit_never_absorbs_a_bystanders_dirty_file` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, AFFECT001@scripts/fleet_status.py, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@scripts/fleet_status.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/release/_cli.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/tickets/_land_git_ops.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, DOC001@docs/commands/release.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT002@scripts/fleet_status.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PERF004@src/frob/app/ticket_runner/_new.py, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK004@tickets.md
