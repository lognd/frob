## Done report

### What changed

`_print_land_proof` (`src/frob/app/ticket_runner/_land_cmd.py`) now also
pops T-2255's `_LAST_ORPHAN_EVIDENCE_OUTCOME[report.ticket_id]` and prints
it as its own `orphan_evidence_check=` field on the `LAND-PROOF:` line,
identical shape to the existing `claims_reverify=` field T-2091 added for
`_LAST_CLAIMS_OUTCOME`: `unknown` when no entry exists (dry run /
recovered-marker path), the raw `.value` (`ran` / `skipped-unmeasured`)
otherwise. No change to the returned `verified` bool -- surfacing only,
exactly as T-2091 was for its own check.

### Evidence

- `TestLandProofOrphanEvidenceOutcome::test_skipped_unmeasured_is_surfaced_not_dropped`
  (T-1929 designated repro, FAILED_AT_PARENT confirmed against 6c3e8e2b4,
  the test-only commit): SKIPPED_UNMEASURED prints as
  `orphan_evidence_check=skipped-unmeasured`, `verified` stays `True`
  (mirrors T-2091's own "surfacing, not refusal" acceptance).
- `test_ran_healthy_path_is_printed`: RAN prints as
  `orphan_evidence_check=ran`.
- `test_no_recorded_outcome_prints_unknown`: no entry -> `unknown`,
  same fallback `claims_reverify=` already uses.

### Pre-existing, unrelated failure noted (not fixed, out of scope)

`TestLandProofClaimsOutcome`'s 3 existing tests (`test_skipped_unmeasured_
is_not_printed_as_verified_true`, `test_passed_healthy_path_is_unchanged`,
`test_no_recorded_outcome_leaves_verified_unaffected`) fail on THIS
worktree's main tip -- confirmed by reverting `_land_cmd.py` to `git show
HEAD:...` (i.e. with NONE of this ticket's changes applied) and re-running:
identical failures, `verified=False` where the test expects `True`. Their
own fixture's `_land_proof_checks` monkeypatch returns `state_ok=False`
(`(True, "done", False)`) while asserting `verified=True` -- a state_ok
semantics mismatch unrelated to T-2091/T-2255/T-2275's own claims/orphan-
evidence wiring, pre-existing on main before this ticket touched anything.
Not fixed here: out of this ticket's scope (a different pre-existing test
fixture bug, not the LAND-PROOF wiring this ticket adds).

### Self-check

Ran T-2280's own new file-local pre-land gate
(`_assert_diff_does_not_add_new_file_local_errors_pre_land`) against this
ticket's own 2-file diff before landing: clean, no new RENDER001 (or any
other registered rule) introduced.

### Gates

`frob check --ticket T-2275`: no findings inside `_print_land_proof`'s own
edited lines (~1268-1360) or the new test class; remaining findings in
`_land_cmd.py` are the same pre-existing set T-2280's Done report already
catalogued by line number, none touched by this diff.

### Filed

None.

### Changed
```
 src/frob/app/ticket_runner/_land_cmd.py | 25 ++++++++-
 tests/test_ticket_land_proof_claims.py  | 97 ++++++++++++++++++++++++++++++++-
 tickets/T-2275/ticket.md                | 24 ++++++--
 3 files changed, 137 insertions(+), 9 deletions(-)
```

### Evidence
- `tests/test_ticket_land_proof_claims.py::TestLandProofOrphanEvidenceOutcome::test_skipped_unmeasured_is_surfaced_not_dropped` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land_proof_claims.py::TestLandProofOrphanEvidenceOutcome::test_ran_healthy_path_is_printed` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land_proof_claims.py::TestLandProofOrphanEvidenceOutcome::test_no_recorded_outcome_prints_unknown` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@scripts/fleet_status.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/release/_cli.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, DOC001@docs/commands/release.md, DOC005@README.md, DOC005@docs/modules/cli.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/lang/_nodes.py, DRIFT002@scripts/fleet_status.py, E402@/home/logan/projects/frob/.claude/worktrees/t-2275/scripts/fleet_status.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2275/scripts/fleet_status.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2275/src/frob/lang/_nodes.py, F541@/home/logan/projects/frob/.claude/worktrees/t-2275/tests/test_ticket_work_and_land_finish.py, F841@/home/logan/projects/frob/.claude/worktrees/t-2275/tests/test_ticket_land.py, PERF004@scripts/fleet_status.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PRE001@tickets/T-2275, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md
