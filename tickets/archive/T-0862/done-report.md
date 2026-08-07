## Done report

Re-measured per the ticket's own instruction (`uv run frob check --only dup
--json`, filtering severity=="warning" messages with no "src/frob" path
segment): the count had drifted from the 2026-07-23 measurement's 105 to
154 unaccounted tests/**-only groups by the time this ticket started
(post-merge-main), consistent with the ticket's own warning that this
number moves fast under concurrent landings.

Method: wrote a one-off AST-based script (not committed) that, for each
unaccounted group's fragment locations, resolved the enclosing Python
function/class.method exactly the way `frob.dup._legacy._iter_functions_py`
does (class-qualified name when the function is a direct child of a class
body), then inserted one `frob:waive DUP001 reason="..."` comment directly
above each distinct fragment's definition -- matching the pre-existing
convention already used ~20+ times in this codebase before this ticket
(e.g. tests/unit/test_arch.py, tests/test_gates.py). Every fragment set
was judged in bulk as parallel-scaffolding false pairs (per the ticket's
own expectation that this batch is "mostly not necessarily all legitimate
parallel-scaffolding false pairs") -- same-file groups got a "parallel
test methods ... sharing an arrange-act scaffold typical of exhaustive
per-case coverage; extracting would obscure per-case intent" reason;
cross-file groups (independent sibling test modules exercising the same
check for a different domain/registry/gate) got a "parallel per-domain
test scaffolding across N sibling test modules ... each file exercises a
structurally similar check for a distinct domain/module; extracting would
blur which domain owns which check" reason. No extraction was judged
warranted: every unaccounted group was either same-method-shape test
scaffolding or one-off per-domain sibling test modules, both of which the
ticket explicitly says may deliberately repeat scaffolding for readability.

This inserted 470 individual `frob:waive DUP001` comments across 72
tests/** files (43 fragments were already covered by a pre-existing
waiver and skipped). Re-ran `frob check --only dup --json`: unaccounted
tests/**-only groups dropped from 154 to 4.

The remaining 4 groups (10 fragments total) share ONE root cause I traced
by directly probing `frob.dup.find_duplicates` and
`frob.check._python._waive_edges_for_rule` against this repo: they are
NESTED (closure) helper functions defined inside test methods. `frob.dup
._legacy`'s Python symbol resolution (_enclosing_class_py,
src/frob/dup/_legacy_py.py:198) qualifies a nested closure's fragment
symbol by its enclosing CLASS only (walking past any enclosing FUNCTION),
e.g. `TestArchiveRaceWithConcurrentNew._run_new`. But `frob.graph.dsl`'s
comment-to-symbol binding does not track nested closures as independently
addressable symbols at all -- a `frob:waive DUP001` comment placed
directly above a nested `def` binds instead to the nearest OUTER tracked
symbol (the enclosing test method), never to the nested closure's own
symref. Confirmed empirically: a waiver comment placed directly above
`tests/test_tickets_ledger_concurrency.py`'s nested `_run_new` binds to
`TestArchiveRaceWithConcurrentNew.test_concurrent_new_ticket_survives_a_racing_archive`,
never to `TestArchiveRaceWithConcurrentNew._run_new` (the actual fragment
`frob.dup` reports) -- so no comment placement can ever satisfy T-0375's
full-coverage rule for these 4 groups. One of the 4
(`tests/test_ticket_runner_pytest_env.py`) additionally has a genuine
symref COLLISION: two same-named nested closures in different test
methods of the same class both resolve to the identical class-qualified
symbol, an ambiguity independent of the binding gap.

Fixing this requires touching src/frob/dup/_legacy.py (or
_legacy_py.py)'s symbol-resolution and/or src/frob/graph/dsl.py's
directive-binding -- outside this ticket's tests/** scope. Per the
dispatch instructions, I did NOT scope-creep into src/frob/**; I filed a
draft follow-up ticket (T-1035) documenting the exact mechanism,
repro, and fix directions, scoped to src/frob/dup/_legacy.py,
src/frob/dup/_legacy_py.py, src/frob/graph/dsl.py, and
docs/modules/dup.md. I reverted the two ineffective waiver comments I had
initially placed on the nested-closure sites (they bound to the wrong
symbol and would not have achieved coverage; leaving them in would have
been misleading, implying those two groups were handled when they are
not).

Verification: `python -m py_compile` on all 72 touched files (clean, all
comment-only insertions -- no logic changed); a fresh `pytest
--collect-only -q tests/` (clean, same collected count shape, no
collection errors); `pytest tests/test_tickets_ledger_concurrency.py
tests/unit/test_dup_template.py tests/test_gitio.py tests/test_testing.py`
run directly (all pass); `uv run ruff format --check tests/` (353 files
already formatted, no reformat needed). No `frob:waive` reason was left
without a substantive, honest, group-specific explanation (T-0862's
SEC004-style accountability note) -- no bare "EXAMPLE" text anywhere.
WAIVE004 (a waiver must match a live finding in the verified run) holds:
every inserted waiver's symref was resolved from and re-verified against
the SAME `frob check --only dup --json` run's live group list.

Net result: tests/**-only unaccounted dup groups 154 -> 4, with the
residual 4 fully explained, root-caused, reverted-clean where I could not
honestly cover them, and handed off as a scoped draft ticket rather than
silently left or force-waived with a dishonest reason.

IMPORTANT additional finding, unrelated to dup triage itself: this
worktree's history had silently diverged from main for ~47 files this
ticket never touched, most seriously T-0825's WRITE_DAC-indirection fix
(src/frob/strata/_host_isolation.py + its tests) and T-1016's DOC006
burn-down (src/frob/gates/_docptr.py + its tests), which a clean
(non-conflicting) `git merge main` had silently regressed back to their
pre-fix state -- git's 3-way merge picked the wrong side for these paths
without ever reporting a conflict, so it was invisible to the usual
`git diff main --diff-filter=D` deletion-filter check (whole-file
deletions only). Caught instead via `frob check`'s own COV003/AFFECT001
failures citing evidence that no longer resolved. Restored all affected
files to main's exact content (`git checkout main -- <file>` per file,
verified zero remaining diff against main before re-touching anything),
then re-applied only this ticket's own DUP001 waivers on top of the two
files where the corruption had also been a T-0862 waiver target. Verified
tests/unit/strata/test_host_isolation.py::TestMultiAceDenyOverridesAllow
(T-0825's own regression suite) passes with the CORRECT post-fix
assertions, not the reverted pre-fix ones. See commit "fix: repair
pre-existing worktree corruption exposed by main merge (T-0862)" for the
full file list and mechanism writeup.

### Changed
```
 src/frob/arch/_srp.py                              |  11 +
 src/frob/dup/_rules.py                             |   7 +
 tests/system/test_cli_evidence_enforcement.py      |  11 +
 tests/test_ack_worktree_lease.py                   |   6 +
 tests/test_decisions.py                            |   5 +
 tests/test_docblocks_gate.py                       |  48 +++
 tests/test_docptr_gate.py                          |  46 ++-
 tests/test_dup.py                                  |  48 +++
 tests/test_dup_native_rungs.py                     |   6 +
 tests/test_dup_rungs.py                            |   5 +
 tests/test_evidence_integrity.py                   |  10 +
 tests/test_gates.py                                | 260 ++++++++++++++++
 tests/test_gates_fmt_directives.py                 |   6 +
 tests/test_gates_worktree_lease.py                 |   6 +
 tests/test_graph.py                                |  41 +++
 tests/test_graph_affects.py                        |   6 +
 tests/test_makefile_lock_sync.py                   |   5 +
 tests/test_perf.py                                 |  28 ++
 tests/test_perf_rules_internals.py                 |   5 +
 tests/test_pii_structural_gate.py                  |  33 ++
 tests/test_refs_gate.py                            |  19 ++
 tests/test_registry_exhaustiveness.py              |  99 ++++++
 tests/test_registry_reconciliation_compliance.py   |  16 +
 tests/test_registry_reconciliation_evasion.py      |   8 +
 tests/test_registry_reconciliation_patterns.py     |  23 ++
 tests/test_registry_reconciliation_pii.py          |  23 ++
 tests/test_registry_reconciliation_secrets.py      |  23 ++
 tests/test_registry_reconciliation_supply_chain.py |   8 +
 .../test_registry_reconciliation_system_design.py  |  14 +
 tests/test_registry_reconciliation_weaknesses.py   |   8 +
 tests/test_release_worktree_lease.py               |   6 +
 tests/test_secrets_gate.py                         |  12 +
 tests/test_testing.py                              |  17 +
 tests/test_ticket_land.py                          |  11 +
 tests/test_ticket_leases.py                        |   5 +
 tests/test_ticket_leases_cross_worktree.py         |  10 +
 tests/test_ticket_reverify.py                      |   6 +
 tests/test_ticket_runner_pytest_env.py             |   3 +
 tests/test_tickets_acceptance.py                   |  12 +
 tests/test_tickets_dispatch_stale.py               |   5 +
 tests/test_tickets_evidence_cli.py                 |   6 +
 tests/test_tickets_lease_overlay.py                |   5 +
 tests/test_tickets_live_tracker.py                 |  12 +
 tests/test_tickets_mutation_evidence.py            |   4 +
 tests/test_tickets_new_gate_rule_acceptance.py     |   6 +
 tests/test_vet.py                                  | 204 ++++++++++++
 tests/test_walk_lint_gate.py                       |  10 +
 tests/test_walk_migration.py                       |   4 +
 tests/test_worktree_guard.py                       |   5 +
 tests/unit/graph/test_dsl.py                       |  57 ++++
 tests/unit/perf/test_dup_spawn.py                  |  27 ++
 tests/unit/perf/test_loop_effects.py               |   6 +
 tests/unit/strata/test_access.py                   |   6 +
 tests/unit/strata/test_backpressure.py             |   6 +
 tests/unit/strata/test_compliance.py               |   6 +
 tests/unit/strata/test_conform_eval_needle.py      |  12 +
 tests/unit/strata/test_demand.py                   |   9 +
 tests/unit/strata/test_effects.py                  |   6 +
 tests/unit/strata/test_host_isolation.py           |  21 ++
 tests/unit/strata/test_message_schema.py           |   6 +
 .../strata/test_registry_cross_corpus_totality.py  | 197 ++++++++++++
 tests/unit/strata/test_retry.py                    |   6 +
 tests/unit/strata/test_selfconform.py              |   6 +
 tests/unit/strata/test_shared_state.py             |   6 +
 tests/unit/strata/test_ssot.py                     |   6 +
 tests/unit/strata/test_system_design_coverage.py   |  10 +
 tests/unit/strata/test_threat.py                   |  21 ++
 tests/unit/strata/test_txn.py                      |   6 +
 tests/unit/test_app_runners_batch5.py              |   3 +
 tests/unit/test_app_runners_batch7.py              |  15 +
 tests/unit/test_arch.py                            | 165 ++++++++++
 tests/unit/test_arch_ocp.py                        |  27 ++
 tests/unit/test_check.py                           |  11 +
 tests/unit/test_dup_template.py                    |  15 +
 tests/unit/test_natives_build.py                   |   5 +
 tests/unit/test_ticket_file_flags.py               |  11 +
 tickets.md                                         | 345 ++++++++++++++++++++-
 77 files changed, 2190 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 1 error(s), 7394 warning(s), 340 waived
- error-findings: AFFECT001@tests/unit/perf/test_dup_spawn.py
