## Done report

Enumerated all six frob check spawn sites under app.ticket_runner (matching the ticket's own grep-derived list, re-verified by direct git grep) and threaded each command's already-resolved effective base ref through to the spawned argv as --base:

- close/reverify's two --only gates spawns (_close_gate_claims_for_ticket, _own_obligations_diff_findings) forward cfg.ticket_base_ref, only when it differs from its own argparse default main (no unset sentinel exists to tell 'explicit --base-ref main' from 'flag omitted')
- the shared spawn close/land/verify feed into (_shared_check_spawn_fn) forwards the same resolved base from each of its three call sites
- land's post-land/pre-commit unscoped sweep argv builder (_unscoped_check_spawn_args, via _unscoped_error_findings) forwards cfg.ticket_land_branch (T-3787's resolved land target, None unless an explicit --branch/--onto or ticket_land_branch default was given)
- land --plan's TICK-gate spawn forwards nothing, DOCUMENTED as deliberate: --plan land has no target-branch concept at all
- the rapid-land detached sweep-async child crosses an actual OS-process boundary this ticket's scope cannot add a new CLI flag for (out of scope: _cli_parsers/), so it hands the base across via a narrow FROB_LAND_TARGET_BRANCH env var instead of an argv flag, documented as the one deliberate exception to threading base as an explicit argument

No base given anywhere is byte-identical to pre-T-4105 behavior (must-stay-quiet fixture): no --base is forwarded, and frob.toml's own check_base default still reaches every nested spawn unchanged (third fixture). Added tests/unit/test_ticket_runner_base_forward_t4105.py covering all three fixtures at the argv/env level for every touched site, including direct mutation-killing coverage of the != main resolution branches (TestCloseGuardsBaseResolution, TestDoneReportBaseResolution), plus updated four pre-existing test files whose close-guard stub lambdas needed a base=None kwarg to keep matching the new signatures.

Filed T-4123 for the ~58 pre-existing SCOPE002 doc-closure findings this ticket's already-declared whole-file scope surfaces (predates this diff; unrelated to the --base fix).

### Changed
```
 src/frob/app/ticket_runner/_close_cmd.py           |  80 ++--
 src/frob/app/ticket_runner/_land_cmd.py            | 108 +++++-
 src/frob/app/ticket_runner/_rapid_sweep.py         |  76 +++-
 src/frob/app/ticket_runner/_verify.py              |  52 ++-
 tests/ticket_land_suite/test_verify_intent.py      |   6 +-
 .../test_app_runners_t0976_mutation_evidence.py    |   8 +-
 tests/unit/test_ticket_close_bug002_t1427.py       |   8 +-
 .../test_ticket_close_own_obligations_t1387.py     |   4 +-
 .../unit/test_ticket_runner_base_forward_t4105.py  | 427 +++++++++++++++++++++
 tickets/T-4105/done-report.md                      |  37 ++
 tickets/T-4105/ticket.md                           | 102 ++++-
 tickets/T-4123/ticket.md                           |  32 ++
 12 files changed, 861 insertions(+), 79 deletions(-)
```

### Evidence
- `tests/unit/test_ticket_runner_base_forward_t4105.py::TestUnscopedCheckSpawnArgsForwardsBase::test_no_base_omits_the_flag` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_base_forward_t4105.py::TestUnscopedCheckSpawnArgsForwardsBase::test_explicit_base_reaches_argv` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_base_forward_t4105.py::TestSharedCheckSpawnFnForwardsBase::test_no_base_omits_the_flag` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_base_forward_t4105.py::TestSharedCheckSpawnFnForwardsBase::test_explicit_base_reaches_argv` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_base_forward_t4105.py::TestCloseGateSpawnsForwardBase::test_gate_claims_no_base_omits_the_flag` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_base_forward_t4105.py::TestCloseGateSpawnsForwardBase::test_gate_claims_explicit_base_reaches_argv` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_base_forward_t4105.py::TestCloseGateSpawnsForwardBase::test_own_obligations_explicit_base_reaches_argv` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_base_forward_t4105.py::TestRapidSweepBaseHandoff::test_detached_sweep_env_sets_the_var_when_given` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_base_forward_t4105.py::TestRapidSweepBaseHandoff::test_detached_sweep_env_omits_the_var_by_default` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_base_forward_t4105.py::TestRapidSweepBaseHandoff::test_spawn_true_count_check_forwards_base_from_env` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_base_forward_t4105.py::TestRapidSweepBaseHandoff::test_spawn_true_count_check_omits_base_when_env_unset` (pytest node id, verified passing when recorded)
- `tests/ticket_land_suite/test_verify_intent.py::TestUnscopedErrorFindingsPublicSeam::test_delegates_with_the_same_arguments` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_base_forward_t4105.py::TestCloseGuardsBaseResolution::test_default_main_resolves_to_no_base_forwarded` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_base_forward_t4105.py::TestCloseGuardsBaseResolution::test_non_main_base_ref_is_forwarded` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_base_forward_t4105.py::TestDoneReportBaseResolution::test_default_main_resolves_to_no_base_forwarded` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_base_forward_t4105.py::TestDoneReportBaseResolution::test_non_main_base_ref_is_forwarded` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 16 passed (from 16 evidence id(s))
- gates: 4 error(s), 4431 warning(s), 937 waived
- error-findings: I001@/home/logan/projects/frob/.claude/worktrees/t-4105/tests/unit/test_ticket_runner_base_forward_t4105.py, PRE001@tickets/T-4105, SCOPE002@tickets.md, missing-argument@tests/unit/test_check_gates_summary.py
