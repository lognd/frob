## Done report

T-0594 wires the T-0569 ratchet-pool mechanism (`frob.gates._ratchet`) into
a real gate's severity resolution, closing the "additive, self-contained,
nothing consumes it yet" gap that ticket's Done report disclosed.

Design: INV006 (`inv006_gate`, src/frob/gates/__init__.py) was chosen as
the warn-first rule to wire, per the ticket's own suggestion. `inv006_gate`
now loads `ratchet_enabled_rules(root)` once per run and, only when
"INV006" is in that set, `load_ratchet_lock(root)` once; both are threaded
down to `_inv006_src_violations`, which calls `resolve_ratchet_severity(
"INV006", rel, lock)` per file to pick the reported `Severity` instead of
the previous unconditional WARN. `rel` (the finding's repo-relative path)
is INV006's natural stable key -- findings are already file-level
(line=0), so no new key scheme was needed. `frob.toml`'s
`[gates.ratchet] rules` now reads `["INV006"]`; this repo's own 29
pre-existing INV006 findings at the point ratcheting was enabled were
baselined with `frob pool snapshot INV006 --key <path> ...`
(frob-ratchet.lock.json, committed) so enabling this did not turn `frob
check` red on its own history -- only a file with a NEW, unbound
exclusivity claim now reports INV006 at ERROR.

Deviations from the dispatch checklist: no _ALL_GATES / _build_jobs /
stage-group / _KNOWN_GATE_RULES / check-coverage.yaml registry / new
frob:enforces changes were made. Those apply to adding a brand-new gate
RULE ID; INV006 already exists as a fully wired, registered gate
(CHK-GATE-INV006 already in check-coverage.yaml, already in
_KNOWN_GATE_RULES/_build_jobs/the invariant stage group). This ticket's
scope, per its own body, is the ONE severity-resolution call site plus
frob.toml/docs -- confirmed against T-0594's ticket text before
implementing, not assumed from the dispatch prompt's generic new-gate
boilerplate.

Evidence: tests/test_gates.py::TestInv006Gate gained four new cases --
fresh finding errors when the rule is ratchet-enabled and unbaselined;
a baselined finding stays warn; the rule stays static WARN with no
[gates.ratchet] opt-in at all (opt-in, not opt-out); and a calibration
test that loads THIS repo's own committed frob.toml + frob-ratchet.lock.json
and asserts every currently-baselined entry resolves to warn while an
unbaselined key resolves to error. All ten TestInv006Gate cases and the
full tests/test_gates.py suite pass. `frob check --ticket T-0594` passes
clean across all five --only stage groups (lint, static, gates-fast,
gates-native, gates-security) after a ruff-format/ruff-check --fix pass
and a `frob ticket sweep T-0594` re-run (the scope-add after `ticket
start` staled the recorded pre-work sweep, PRE001).

Files touched: src/frob/gates/__init__.py (import + inv006_gate/
_inv006_src_violations wiring), frob.toml ([gates.ratchet] rules =
["INV006"] + comment), docs/modules/gates.md (Ratchet pools section
updated to describe the live wiring), tests/test_gates.py (four new
TestInv006Gate cases + _ratchet imports), frob-ratchet.lock.json (new,
committed baseline of this repo's 29 pre-existing INV006 findings).

The deletion-filter check (`git diff main --diff-filter=D --stat`) showed
one unrelated deletion (src/frob/app/agent_runner.py) against the LOCAL
`main` branch ref, which is 108 commits behind origin/main in this
worktree's git config; re-run against `origin/main` (the true current
tip, and an ancestor of this worktree's HEAD per `git merge-base
--is-ancestor origin/main HEAD`) is clean -- no unintended deletions.

### Changed
```
 .frob-release.json                               |   73 +-
 CHANGELOG.md                                     |   68 +
 design/frob.strata                               |   72 +-
 docs/audits/frob-blindspots-2026-07-23.md        |  256 +
 docs/design/registry/check-coverage.yaml         |   14 +-
 docs/design/registry/compliance.yaml             |   58 +-
 docs/design/registry/supply-chain.yaml           |    6 +-
 docs/design/registry/weaknesses.yaml             |   26 +
 docs/design/security-corpus.md                   |   56 +-
 docs/design/supply-chain-corpus.md               |   27 +-
 docs/design/system-design-corpus.md              |   63 +-
 docs/guides/extending/test-runner-entries.md     |   37 +
 docs/index.md                                    |    3 +
 docs/modules/arch.md                             |   57 +
 docs/modules/cli.md                              |   39 +
 docs/modules/gates.md                            |  105 +
 docs/modules/graph.md                            |  130 +-
 docs/modules/perf.md                             |   75 +-
 docs/modules/serve.md                            |   75 +-
 docs/modules/testing.md                          |   59 +
 docs/modules/tickets.md                          |   36 +
 docs/modules/vet.md                              |    7 +
 docs/strata/host.md                              |   73 +-
 pyproject.toml                                   |    2 +-
 src/frob/__init__.py                             |   40 +-
 src/frob/__main__.py                             |   37 +-
 src/frob/app/__init__.py                         |   54 +-
 src/frob/app/check_runner.py                     |  101 +-
 src/frob/app/config.py                           |    9 +
 src/frob/app/docs_runner.py                      |    9 +-
 src/frob/app/fleet_runner.py                     |   36 +-
 src/frob/app/gitlog_runner.py                    |   35 +-
 src/frob/app/map_runner.py                       |    9 +-
 src/frob/app/mutate_runner.py                    |   18 +-
 src/frob/app/outline_runner.py                   |    7 +
 src/frob/app/ticket_runner.py                    |  179 +-
 src/frob/app/xref_runner.py                      |    7 +
 src/frob/arch/__init__.py                        |    3 +-
 src/frob/arch/_concurrency.py                    |  352 ++
 src/frob/arch/_models.py                         |   10 +
 src/frob/check/__init__.py                       |   21 +-
 src/frob/deploy/_vm_runner.py                    |   25 +-
 src/frob/dup/_cache.py                           |   39 +-
 src/frob/dup/_pipeline.py                        |  152 +-
 src/frob/fleet/__init__.py                       |   22 +-
 src/frob/gates/__init__.py                       |  771 ++-
 src/frob/gates/_exclude_hazard.py                |   28 +-
 src/frob/gates/_protocol_summary.py              |  180 +
 src/frob/gitio.py                                |  230 +-
 src/frob/gitlog/__init__.py                      |   16 +-
 src/frob/graph/__init__.py                       |   87 +-
 src/frob/graph/_models.py                        |   30 +
 src/frob/graph/callgraph.py                      |  164 +-
 src/frob/graph/dsl.py                            |  249 +-
 src/frob/graph/summary.py                        |  517 ++
 src/frob/logging/__init__.py                     |    3 +-
 src/frob/logging/quiet.py                        |   25 +
 src/frob/mutate/__init__.py                      |   38 +-
 src/frob/perf/_collectors.py                     |  388 ++
 src/frob/perf/_rules.py                          |  124 +-
 src/frob/scaffold/project.py                     |   25 +-
 src/frob/serve/__init__.py                       |    2 +
 src/frob/serve/_daemon.py                        |  421 ++
 src/frob/serve/_tools.py                         |   29 +
 src/frob/serve/server.py                         |   28 +-
 src/frob/strata/__init__.py                      |    4 +
 src/frob/strata/_compliance.py                   |  140 +
 src/frob/strata/_effects.py                      |  165 +-
 src/frob/strata/_host_isolation.py               |  389 +-
 src/frob/strata/_scenarios.py                    |   24 +-
 src/frob/strata/_selfconform.py                  |  140 +-
 src/frob/testing/_coverage_wait.py               |   20 +-
 src/frob/testing/_models.py                      |    7 +-
 src/frob/testing/_runners.py                     |   15 +
 src/frob/tickets/__init__.py                     |  315 +-
 src/frob/tickets/_land.py                        |  836 ++-
 src/frob/tickets/_leases.py                      |  599 +-
 src/frob/tickets/_models.py                      |   14 +
 src/frob/tickets/_store.py                       |   46 +-
 src/frob/tickets/clipboard.py                    |   56 +-
 src/frob/vet/_capability.py                      |  145 +-
 src/frob/vet/_capability_modes.py                |  311 +
 src/frob/vet/_nvd.py                             |   14 +
 src/frob/vet/_registry.py                        |   17 +
 src/frob/vet/_scan.py                            |   90 +-
 tests/integration/test_fleet_integration.py      |   35 +
 tests/integration/test_mutate_runner.py          |   75 +
 tests/system/test_cli_check.py                   |  218 +-
 tests/system/test_cli_doctor.py                  |    1 +
 tests/system/test_spawn_budget.py                |  134 +
 tests/test_app.py                                |   35 +-
 tests/test_clipboard.py                          |   34 +
 tests/test_dup.py                                |  282 +
 tests/test_gates.py                              |  404 ++
 tests/test_gitio.py                              |  174 +-
 tests/test_graph.py                              |  131 +
 tests/test_mutate.py                             |   46 +
 tests/test_perf.py                               |   79 +
 tests/test_perf_loop_invariant_effect_lock.py    |   79 +
 tests/test_registry_reconciliation_compliance.py |   89 +-
 tests/test_serve.py                              |   11 +-
 tests/test_serve_daemon.py                       |  294 +
 tests/test_ticket_land.py                        | 1007 +++-
 tests/test_ticket_runner_archive_force.py        |  132 +
 tests/test_ticket_runner_quiet.py                |   41 +
 tests/test_tickets.py                            |   89 +
 tests/test_tickets_dispatch_stale.py             |  178 +
 tests/test_tickets_evidence_cli.py               |  148 +
 tests/test_tickets_lease.py                      |   32 +
 tests/test_tickets_leases.py                     |  604 ++
 tests/test_vet.py                                |   83 +-
 tests/test_vet_capability.py                     |  122 +
 tests/test_waive_gate.py                         |  578 ++
 tests/unit/deploy/test_vm_runner.py              |   43 +-
 tests/unit/fleet/test_status.py                  |   45 +
 tests/unit/graph/test_cache.py                   |  144 +
 tests/unit/graph/test_dsl.py                     |  198 +
 tests/unit/perf/fixtures/sample.cpuprofile       |   21 +
 tests/unit/perf/fixtures/sample.jfr.txt          |   18 +
 tests/unit/perf/fixtures/sample.perf.script      |   11 +
 tests/unit/perf/test_collectors.py               |  237 +
 tests/unit/strata/test_compliance.py             |   72 +
 tests/unit/strata/test_effects.py                |   88 +-
 tests/unit/strata/test_host_isolation.py         |  259 +
 tests/unit/strata/test_selfconform.py            |   57 +-
 tests/unit/test_app_runners_batch6.py            |   34 +-
 tests/unit/test_app_runners_batch7.py            |    2 +-
 tests/unit/test_arch.py                          |  486 ++
 tests/unit/test_gitlog.py                        |   28 +
 tests/unit/test_logging_quiet.py                 |   50 +
 tests/unit/test_scaffold_project.py              |   34 +
 tests/unit/test_ticket_runner_land_release.py    |   31 +-
 tests/unit/vet/__init__.py                       |    0
 tests/unit/vet/test_capability_modes.py          |  105 +
 tickets-archive.md                               | 4727 ++++++++++++++-
 tickets.md                                       | 6724 +++++++++++++++++-----
 uv.lock                                          |    2 +-
 137 files changed, 25503 insertions(+), 2332 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestInv006Gate::test_ratchet_fresh_finding_errors_when_rule_enabled` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestInv006Gate::test_ratchet_baselined_finding_stays_warn` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestInv006Gate::test_ratchet_rule_not_enabled_stays_static_warn` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestInv006Gate::test_this_repos_frob_toml_and_ratchet_lock_calibrate` (pytest node id, verified passing when recorded)
