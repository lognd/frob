## Done report

Root cause found: `_parse_error_findings_from_json` (src/frob/app/
ticket_runner/_verify.py, OUT of this ticket's declared scope, filed
separately as T-2349) does `findings.add((d.get("code") or "", d.get(
"file") or ""))` for every error-severity diagnostic -- a diagnostic
missing BOTH fields becomes a genuine ("", "") member of the returned
set, which then flows into `_rapid_sweep.py`'s rolling-baseline diff and
gets rendered as a blank "-   " line in a filed ticket body, exactly as
observed in T-2297.

Fix, within this ticket's own scope: `_normalize_identities`
(src/frob/app/ticket_runner/_rapid_sweep.py) -- the single choke point
every producer/consumer of an identity set in this module already
routes through (T-2036's own precedent) -- now drops any pair where BOTH
rule and file are empty, logging a WARNING with the dropped count. A
pair with only ONE field empty is left alone (still a real, if partial,
identity, not the T-2313 shape).

Positive control: verified the fix does NOT break real identity
handling -- TestNormalizeIdentityFile (3 tests, path normalization),
TestRollingBaseline, and TestAbsoluteVsRelativePathIdentityMismatch
(T-2036's own sibling-format-drift regression) all still pass, plus a
dedicated test asserting a well-formed pair and a partial (one-field)
pair both survive normalization untouched.

Repro verified genuine, not confirmatory-only: committed the test alone
first (d577dae72), confirmed it FAILS against the pre-fix
_normalize_identities (checked out the old file on top of the new test,
ran it directly -- AssertionError, the ("", ".") pair survives), then
applied the fix and confirmed it passes. `frob ticket evidence T-2313
--check-repro ... --base-ref d577dae72` independently confirms
FAILED_AT_PARENT.

Verified: `pytest tests/unit/test_rapid_sweep.py` -- 112 passed (full
file, not just the new tests).

Filed: T-2349 (the actual root-cause fix in _verify.py, out of this
ticket's scope).

### Changed
```
 src/frob/app/ticket_runner/_rapid_sweep.py | 40 ++++++++++++++++++++++----
 tests/unit/test_rapid_sweep.py             | 45 ++++++++++++++++++++++++++++++
 tickets/T-2313/ticket.md                   | 10 +++++--
 3 files changed, 88 insertions(+), 7 deletions(-)
```

### Evidence
- `tests/unit/test_rapid_sweep.py::TestNormalizeIdentities::test_drops_genuinely_empty_identity_pair` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestNormalizeIdentities::test_leaves_well_formed_pairs_untouched` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestNormalizeIdentities::test_partial_identity_one_field_empty_is_kept` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@scripts/fleet_status.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/release/_cli.py, COV001@scripts/fleet_status.py, COV001@src/frob/tickets/_land_git_ops.py, COV001@src/frob/tickets/_leases.py, COV001@src/frob/verify/_drain.py, COV001@src/frob/verify/_quarantine.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, DOC001@docs/commands/release.md, DOC002@scripts/fleet_status.py, DOC002@src/frob/app/verify_runner.py, DOC002@src/frob/verify/_drain.py, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT002@src/frob/verify/_drain.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2313/src/frob/verify/_worker.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_new.py, PRE001@tickets/T-2313, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/tickets/_leases.py, TICK004@tickets.md, WIRE003@docs/modules/cli.md
