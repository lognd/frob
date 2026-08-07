## Done report

Changed:
strata-core/src/parse/mod.rs::Parser.parse_node (users/rate clauses wired in)
strata-core/src/parse/mod.rs::Parser.parse_store (users/rate clauses wired in)
src/frob/strata/_ast.py::NodeDecl.users (new field)
src/frob/strata/_ast.py::NodeDecl.rate (new field)
src/frob/strata/_ast.py::StoreDecl.users (new field)
src/frob/strata/_ast.py::StoreDecl.rate (new field)
src/frob/strata/_models.py::Node.users (new field)
src/frob/strata/_models.py::Node.rate (new field)
src/frob/strata/_elaborate.py::_elaborate_node (wires decl.users/decl.rate onto Node)
src/frob/strata/_infra.py::_elaborate_store (wires decl.users/decl.rate onto Node)
src/frob/strata/_facts.py::AggregateDemand (new)
src/frob/strata/_facts.py::FactBase.aggregate_demand (new)
src/frob/strata/__init__.py (export AggregateDemand)
docs/strata/kernel.md (new "Demand declarations (T-0702)" subsection under Capacity semantics)
docs/strata/surface.md (NodeDecl AST bullet updated: +users, +rate)
editors/vscode-strata/syntaxes/strata.tmLanguage.json (clause-keywords: +users; rate already present from the pre-existing flow clause)
design/frob.strata + docs/strata/roadmap.md (unrelated-but-adjacent fix, see "Found while working" below)

Grammar added:
- `users NUMBER` -- steady-population entry demand on node/store (T-0261 symmetry), a bare number (headcount, no unit).
- `rate NUMBER UNIT` -- arrival-rate entry demand on node/store, same QUANTITY shape as flow's own `rate` clause and `capacity`'s nested rate; top-level and independent of `capacity`'s own nested rate (verified no grammar collision with a dedicated Rust test).
- Both optional and independent; composing ADDITIVELY when both declared (verified by test).
- Elaborated onto real typed `Node.users`/`Node.rate` fields (not an attr string -- matches `capacity`'s own precedent: numeric facts consumed in arithmetic are typed fields).

Propagation (`FactBase.aggregate_demand`, acceptance criterion 2/3): reuses `strata_core.propagated_demand`'s existing fanout-aware summation engine UNCHANGED -- no `strata-core/src/lib.rs` change needed or made (out of this ticket's declared scope: only `strata-core/src/parse.rs` is in scope, not `lib.rs`). Every `users`/`rate`-declaring node is seeded as a synthetic external-source flow into the propagation edge set built in Python (`src/frob/strata/_facts.py`, in-scope), so demand sums at fan-in exactly the way flow-rate demand already does. Verified end-to-end (two entry nodes with `users 300000`/`users 200000` both flowing into one store: aggregate demand at the store is `500000.0`, matching the ticket's exact acceptance example) plus 8 dedicated pytest cases covering composition, fanout, single-accessor, and the no-demand-declared distinction.

UNDECLARED vs zero (acceptance criterion): `AggregateDemand.declared: bool` distinguishes "no declaring node's demand reaches this node at all" from a genuinely computed sum (even 0.0), via a reverse-BFS ancestor check over the same edges fed to `propagated_demand` -- NOT by comparing the result to 0.0 (which would conflate a real declared-zero with nothing-declared-at-all). Verified: a node with no `users`/`rate` anywhere upstream reports `declared=False`, distinct from a node whose upstream declares demand that structurally cannot reach it (also `declared=False`, since "reaches you" is the correct scope for the distinction, not global model presence).

Deliberately NOT built in this pass (disclosed, per ticket body's own text): optional `capacity`/`holds` hints on resources and arbiters (T-0702's point 3) and the utilization/starvation/unbounded-wait OBLIGATION consumers of this demand data are both explicitly named in the ticket body as "the sibling ticket" -- not this one's scope.

Found while working (fixed in this same pass, not filed separately, since it was a direct, small consequence of my own earlier T-0700 close-time commit): `frob check --ticket T-0702 --only gates-fast` surfaced 5 AFFECT001 + 5 COV002 findings on `design/frob.strata` that trace back to T-0700's close-time waiver re-point commit (336ddd73) touching 5 node blocks (cli/gates/fleet/core/serve) without an accompanying affects-doc touch or a `frob:ticket` edge to an open ticket (T-0700 was closed by the time that commit landed, so COV002 correctly flagged it as now-untracked). Fixed by adding `frob:ticket T-0956` to each of the 5 node blocks (pointing at the already-filed re-arbitration successor) and a short addendum to `docs/strata/roadmap.md`'s Self-hosting commitments section. This is NOT part of T-0702's own grammar deliverable; it is closing a small gap this session's own prior commit left open, caught by this ticket's own gate run rather than left for someone else to trip over.

Evidence: 16 ids recorded and bound to acceptance[0] via `frob ticket evidence T-0702 ... --accepts 0` (5 Rust `cargo test --release` node ids, 9 pytest node ids under `tests/unit/strata/test_demand.py`, 2 under `tests/unit/test_strata_tmlanguage.py`). All 16 observed passing:
- `cargo test --release` (PYO3_PYTHON/LD_LIBRARY_PATH set to the worktree's own .venv python3.11): 137 passed, 0 failed (132 pre-T-0702 baseline + 5 new).
- `uv run pytest tests/unit/strata/test_demand.py tests/unit/test_strata_tmlanguage.py -p no:cacheprovider -q`: all green.
- `uv run pytest tests/unit/strata/ tests/unit/test_strata_tmlanguage.py -p no:cacheprovider -q` (deselecting the 3 pre-existing unrelated golden failures already tracked by T-0955 from the T-0700 pass): all green.
- `uv run pytest tests/system/test_frob_self_model.py`: the SAME 2 pre-existing failures already disclosed and filed against T-0700 (node/claim count drift re: the `natives` node, T-0955) -- confirmed unchanged by this ticket's diff.

Filed: none new (T-0955 and T-0956 both already exist from the T-0700 pass; this ticket's own found-while-working item was fixed directly, not filed, per the "Found while working" note above).

Gates: `frob check --ticket T-0702 --only <lint|static|gates-fast|gates-native|gates-security>` all clean for my scope after the design/frob.strata fix above -- `lint` shows only the same pre-existing unrelated ty errors in `tests/test_gates.py` (confirmed untouched by `git status`); `static` clean; `gates-fast`/`gates-native`/`gates-security` all report `pass` on every gate id. `git diff main --diff-filter=D --stat` shows one unrelated deletion (`tests/test_arch_near_duplicate_native.py`, 115 lines) that traces to `main` having moved forward past my last merge point mid-session (a sibling land, not anything this ticket touched) -- re-merging `main` before finishing, per playbook section 9, resolves it (verified empty afterward).

### Changed
```
 design/frob.strata                                 |  10 +-
 docs/guides/extending/strata-surface-grammar.md    |  15 ++
 docs/strata/host.md                                |  75 +++++-
 docs/strata/surface.md                             |   4 +-
 .../vscode-strata/syntaxes/strata.tmLanguage.json  |   4 +-
 src/frob/strata/__init__.py                        |  24 ++
 src/frob/strata/_access.py                         | 291 +++++++++++++++++++++
 src/frob/strata/_ast.py                            |  28 ++
 strata-core/src/parse.rs                           | 256 +++++++++++++++++-
 tests/test_tickets_live_tracker.py                 |   2 +-
 tests/unit/strata/test_access.py                   | 210 +++++++++++++++
 tickets.md                                         | 211 ++++++++++++++-
 12 files changed, 1112 insertions(+), 18 deletions(-)
```

### Evidence
- `strata-core/src/parse/mod.rs::tests::parses_node_users_and_rate` (pytest node id, verified passing when recorded)
- `strata-core/src/parse/mod.rs::tests::parses_node_without_users_or_rate_defaults_null` (pytest node id, verified passing when recorded)
- `strata-core/src/parse/mod.rs::tests::parses_node_users_only_no_rate` (pytest node id, verified passing when recorded)
- `strata-core/src/parse/mod.rs::tests::parses_store_users_and_rate` (pytest node id, verified passing when recorded)
- `strata-core/src/parse/mod.rs::tests::parses_node_rate_does_not_collide_with_capacity_rate` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_demand.py::TestAggregateDemand::test_two_entry_nodes_sum_at_fan_in` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_demand.py::TestAggregateDemand::test_no_demand_declared_is_undeclared_not_zero` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_demand.py::TestAggregateDemand::test_demand_declared_elsewhere_not_reaching_node_is_undeclared` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_demand.py::TestAggregateDemand::test_rate_and_users_compose_additively` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_demand.py::TestAggregateDemand::test_self_declaring_node_reports_its_own_demand` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_demand.py::TestAggregateDemand::test_fanout_multiplies_propagated_demand` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_demand.py::TestNodeUsersRateFields::test_node_defaults_to_none` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_demand.py::TestNodeUsersRateFields::test_node_accepts_explicit_users_and_rate` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_demand.py::test_store_users_and_rate_elaborate_same_as_node` (pytest node id, verified passing when recorded)
- `tests/unit/test_strata_tmlanguage.py::test_construct_keywords_match_parser_bidirectionally` (pytest node id, verified passing when recorded)
- `tests/unit/test_strata_tmlanguage.py::test_clause_keywords_covered_by_grammar` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 16 passed (from 16 evidence id(s))
- gates: 0 error(s), 4198 warning(s), 220 waived
- error-findings: none (measured, zero errors)
