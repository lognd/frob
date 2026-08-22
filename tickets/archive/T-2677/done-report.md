## Done report

Changed:
- scripts/fleet_status.py::_resolve_repo_root (new)
- scripts/fleet_status.py::REPO (now resolved via _resolve_repo_root)
- tests/unit/test_coordinator_scripts.py::TestResolveRepoRoot (new)
- docs/guides/coordinator-scripts.md#fleet_status-constants (updated)

Root cause: REPO derived from Path(__file__).resolve().parent.parent, so
running the tracked script from inside a linked worktree resolved REPO to
that worktree's own root. A worktree's .git is a FILE (gitdir pointer),
not a directory, so LEASES/QUARANTINE/VERIFY_QUEUE/VERIFY_WATERMARK all
silently resolved to paths that could never exist -- fleet-wide "0 live
leases" from any worktree. This is the DECLARE-NEVER-HARDCODE class
(PORT001's territory), fixed by resolving REPO via
`git rev-parse --path-format=absolute --git-common-dir` (the same
primitive frob.gitio.git_common_dir uses elsewhere for this exact
worktree-vs-common-dir distinction), with a __file__-derived fallback
only if git itself is unavailable.

Positive controls (both directions, measured directly):
- Ran `uv run python scripts/fleet_status.py` from inside
  .claude/worktrees/t2677-series and from the primary checkout
  (via `uv run python .claude/worktrees/t2677-series/scripts/fleet_status.py`)
  immediately after: both reported the IDENTICAL LEASES section --
  "LEASES 7 (6 live, 0 leaked, 0 blocked-open)" with the same 7 entries,
  same statuses -- for the same real fleet state. Before the fix, the
  worktree invocation reported 0 live leases fleet-wide (matching the
  ticket's own measured repro).
- test_falls_back_when_not_a_git_checkout covers the non-git-checkout
  fallback path.
- BUG002 repro designated and verified via `frob ticket evidence
  --check-repro`: the new positive-control test FAILED_AT_PARENT (commit
  0549e1a12, test-only, pre-fix code) -- a genuine repro, not
  confirmatory-only.

Evidence:
- tests/unit/test_coordinator_scripts.py::TestResolveRepoRoot::test_positive_control_matches_primary_checkout (designated repro)
- tests/unit/test_coordinator_scripts.py::TestResolveRepoRoot::test_falls_back_when_not_a_git_checkout

Full tests/unit/test_coordinator_scripts.py suite: 182 passed, 0 failed
(uv run pytest -q tests/unit/test_coordinator_scripts.py).

Filed: none

Gates: `frob check --ticket T-2677` clean of new findings -- baseline
error count 84 before the fix (including this ticket's own new ARCH103
hit on _resolve_repo_root from an early draft), 83 after restructuring
the helper to avoid the I/O+format+branch mixed-concern shape (dropped
the redundant str(fallback) call, since subprocess.run already accepts
Path directly); no ARCH103, SCOPE001, or PRE001 finding remains against
scripts/fleet_status.py, tests/unit/test_coordinator_scripts.py, or
docs/guides/coordinator-scripts.md. Remaining errors in the full report
are pre-existing and outside this ticket's scope (CYCLE001, other
ARCH103 instances, COV003/COV004/DOC002/DOC006 on unrelated tickets).

### Changed
```
 docs/guides/coordinator-scripts.md     | 26 +++++++++++++++----
 scripts/fleet_status.py                | 46 ++++++++++++++++++++++++++++++++--
 tests/unit/test_coordinator_scripts.py | 44 ++++++++++++++++++++++++++++++++
 tickets/T-2677/ticket.md               | 20 +++++++++++++--
 4 files changed, 127 insertions(+), 9 deletions(-)
```

### Evidence
- `tests/unit/test_coordinator_scripts.py::TestResolveRepoRoot::test_positive_control_matches_primary_checkout` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestResolveRepoRoot::test_falls_back_when_not_a_git_checkout` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 45 error(s), 855 warning(s), 680 waived
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC002@src/frob/gates/_milestone.py, DOC006@tickets/T-2691/ticket.md, DOC006@tickets/T-2703/ticket.md, DOC006@tickets/T-2704/ticket.md, DOC006@tickets/T-2705/ticket.md, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII010@src/frob/deploy/_audit.py, PII012@src/frob/doctor.py, PII012@src/frob/serve/_socketd.py, PII012@tests/system/test_cli_doctor.py, PII012@tests/test_capability_registry.py, PII012@tests/test_doctor.py, PII012@tests/test_hook_diagnosis_nudge.py, PII012@tests/test_prework_parity.py, PII012@tests/test_vet.py, PII012@tests/unit/test_doctor_runner_t1276.py, RENDER001@src/frob/release/_cli.py, SEC004@tests/test_tickets_organization.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
