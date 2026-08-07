## Done report

Burned down all 16 unwaived SEC110 (env-secret-read) findings to zero,
then promoted SEC110 from WARN to ERROR in frob.toml's [gates.severity].

Scope note: the ticket's own scope glob list omitted src/frob/gates/
__init__.py even though its Plan text named 3 of the 16 findings there
(lines 8995/10439/10602-ish at ticket-open time, actually 9010/10467/
10630 by pickup). Extended scope via `frob ticket scope T-0973 --add`
(3 scope-change entries, reasons recorded in the audit trail) to cover
that file plus 3 doc files needed for AFFECT001 (see below) plus
tests/test_gates.py for the new severity-promotion fixture test.

Per-site disposition (all fixed via frob:waive, none required a
std.secrets mapping -- every one is a behavior flag, an internal
process-state marker, a cache-dir path, or a test-only synthetic var,
not an actual secret):

- src/frob/app/check_runner.py:857 (`_FROB_AGENT_ENV`) -- waived,
  worktree-agent detection flag.
- src/frob/app/check_runner.py:859 (`_FROB_ALLOW_FULL_CHECK_ENV`) --
  waived, opt-in escape-hatch flag.
- src/frob/gates/__init__.py:9010ish (`_rel001_bump_suppressed_under_agent`,
  reads "FROB_AGENT") -- waived, worktree-agent detection flag. (found
  during the scope-extension above; not originally in the ticket's
  scope glob list.)
- src/frob/gates/__init__.py:10467ish (`_WORKER_STDOUT_LOG_LEVEL_ENV`
  read in the mp-worker wrapper) -- waived, worker log-level marker.
- src/frob/gates/__init__.py:10630ish (same env var, write side in the
  parent before spawning workers) -- waived, worker log-level marker.
- src/frob/perf/_harness.py:110 (`SERIAL_POOLS_ENV_VAR`) -- waived,
  pool-serialization behavior toggle.
- src/frob/perf/_harness.py:114 (`_SAMPLE_ENV_VAR`) -- waived,
  stack-sampling opt-in flag.
- src/frob/tickets/_land.py:107/108/115 (`FROB_LAND_INTERNAL` get/set/
  restore, all 3 sites in `_land_internal_git_env`) -- waived, internal
  reentrancy marker used only to unlock land's own pre-commit hook
  around land's own commits.
- src/frob/tickets/_worktree_guard.py:68 (`FROB_WORKTREE_ENV`) --
  waived, worktree-lease path marker.
- tests/test_testing.py:901/902/903 -- already-waived pre-ticket
  (synthetic test-only var the test itself sets via monkeypatch);
  confirmed still correctly waived, untouched.
- tests/test_ticket_land.py:3825/3828/3831/3832 (all 4 reads/writes of
  `FROB_LAND_INTERNAL` inside
  `test_land_internal_git_env_restores_prior_value`) -- waived,
  synthetic test-only var this test itself sets.
- tests/test_tickets_mutation_evidence.py:305 (`MUTATION_RUN_ENV`) --
  waived, mutation-harness run-mode flag this test's own harness sets.

10 sites were already waived before this ticket (stats_runner.py:27,
telemetry.py:47, process/_guard.py:67, render/_color.py:57,
testing/_runners.py:390/400, vet/_source.py:35, and the 3
test_testing.py sites above) -- left untouched, re-verified they still
resolve as WAIVE-suppressed (0 WAIVE004 regressions against them).

No site turned out to be a real secret needing a std.secrets (T-0082)
mapping -- every one of the 16 was, on inspection, a boolean/enum
behavior flag, an internal reentrancy/log-level marker, a cache-dir
path, or a test's own synthetic monkeypatched var.

Promotion: added `SEC110 = "error"` to frob.toml's [gates.severity]
table (with a comment recording the T-0973 rationale). Verified via
`uv run frob check --only gates-security` (after `make core` -- a
fresh worktree without natives built shows unrelated gate:SYS/gate:DRIFT
failures that are environment artifacts, not regressions; confirmed by
re-running after `make core` and both going green): gate:SEC now shows
0 errors, 0 warnings, 26 waived (all 26 SEC110 findings across the repo
now report at "note" severity, i.e. waived).

T-0756 acceptance-policy note: SEC110 is not a NEW rule id (it predates
this ticket in `_KNOWN_GATE_RULES`), so the mechanical
`new_gate_rule_ids`/`--accepts` DONE-transition gate does not fire for
this change (it only gates rule ids absent at `base_ref`'s tip) --
disclosing this rather than force-fitting an `--accepts` binding that
the tooling itself would not require. In the spirit of that policy's
before-fails/after-passes proof requirement, added
`tests/test_gates.py::TestSeverityOverrides::
test_sec110_promoted_to_error_gates_a_real_repo_toml` as a real fixture:
it asserts a SEC110 finding stays WARN under an empty severity table
(the FAIL case, i.e. pre-T-0973 posture) and is promoted to ERROR under
this repo's own current frob.toml (the PASS case, i.e. post-T-0973
posture) -- proving the promotion is live and load-bearing, not just a
parseable TOML line.

Also touched (AFFECT001, doc-drift obligation): docs/modules/gates.md
(SEC110's "Public API" surface note + a T-0973 paragraph in the PII010/
SEC110 prose section), docs/modules/perf.md ("Integration points" --
`main`'s two env-var waivers), docs/modules/tickets.md ("Worktree-lease
guard (T-0431)" -- `enforce_worktree_lease`'s waiver) -- required
because 3 of the touched functions
(`_rel001_bump_suppressed_under_agent`, `perf._harness.main`,
`_worktree_guard.enforce_worktree_lease`) have `affects()`-closure doc
edges, and adding an inline `frob:waive` comment changes those
functions' digests.

Formatting incident (self-caught, self-corrected): an early
`ruff format` invocation over a batch of touched files accidentally
included two files never in this ticket's scope
(src/frob/arch/_lock_ordering.py, tests/unit/test_arch.py) that
happened to already need reformatting on `main`. Reverted both via
`git checkout -- <path>` before finishing; `git diff main -- <path>`
confirms zero net change to either. `git diff main --diff-filter=D
--stat` is empty (deletion-filter check, playbook section 9).

Full stage-group sweep (post-`make core`, all via the chunked
`--only`-loop, none exceeding the foreground budget):
- gates-security: 0 errors (was the target stage; gate:SEC 0/0/26
  waived).
- gates-fast: 0 errors, --ticket T-0973 scoped.
- gates-native: 0 errors.
- lint (ruff-check/ruff-format/ty): 0 errors, 0 warnings for every
  file this ticket touched (the 2 remaining ruff-format warnings,
  src/frob/arch/_lock_ordering.py and tests/unit/test_arch.py, are
  pre-existing on main, outside this ticket's scope, and were
  reverted-to as noted above, not left dirty by this ticket).
- static: pass (frob-cycle/frob-dup/frob-arch/frob-exports all
  pre-existing-warning-only, unaffected by this diff).

Targeted pytest (foreground, all pass):
- tests/test_gates.py::TestSeverityOverrides (3 passed)
- tests/test_ticket_land.py::TestLandInternalEnvThroughHook::
  test_land_internal_git_env_restores_prior_value (1 passed)
- tests/test_worktree_guard.py (22 passed, full file)
- tests/unit/perf/test_harness_sampling.py (6 passed, full file)
- tests/unit/test_app_runners_batch6.py::TestCheckRunner (targeted
  subset, passed)
- tests/test_testing.py (full file, 73 passed)

One pre-existing, unrelated failure disclosed rather than hidden:
tests/test_tickets_mutation_evidence.py::TestCheckTicketMutationEvidence::
test_confirmatory_test_flagged fails identically against main's
unmodified copy of the file (verified by swapping in `git show main:
tests/test_tickets_mutation_evidence.py` in place, re-running the exact
same test, seeing the same `assert 0 == 1`, then restoring my version) --
not caused by this ticket's one-line waive-comment change to a
different test's env-var guard in the same file. Not filed as a new
ticket by this agent since T-0973's scope does not cover investigating
it; flagging here so it is not silently attributed to this change.

Filed: none (the only out-of-scope discovery, the gates/__init__.py
sites named in the ticket's own Plan text, was resolved by extending
this ticket's own scope rather than opening a sibling ticket, since the
Plan already claimed that work as part of T-0973).

### Changed
(no changed files detected)

### Evidence
- `tests/test_gates.py::TestSeverityOverrides::test_sec110_promoted_to_error_gates_a_real_repo_toml` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestLandInternalEnvThroughHook::test_land_internal_git_env_restores_prior_value` (pytest node id, verified passing when recorded)
- `tests/test_worktree_guard.py::TestEnforceWorktreeLease::test_matching_worktree_passes` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_harness_sampling.py::TestHarnessSerialPoolsDecision::test_env_zero_skips_serial_pools` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_harness_sampling.py::TestHarnessSampling::test_sampled_run_logs_hotgraph_summary` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_bare_check_refuses_under_frob_agent` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_allow_full_check_override_bypasses_refusal` (pytest node id, verified passing when recorded)
- `tests/test_tickets_mutation_evidence.py::TestEvidenceTestIds::test_filters_non_node_id_entries` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 8 passed (from 8 evidence id(s))
- gates: 0 error(s), 5006 warning(s), 236 waived
- error-findings: none (measured, zero errors)
