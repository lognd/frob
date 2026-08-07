## Done report

Changed:
- strata-core/src/lib.rs::worst_age (bug fix: zero/negative-net cycles no
  longer produce spurious +inf; only a positive-age cycle reaching the
  target does)
- strata-core/src/lib.rs::worst_age_visit
- strata-core/src/lib.rs (new: find_positive_cycle, has_positive_cycle_reaching)
- strata-core/src/parse/mod.rs::parse_store (new `rpo QUANTITY` store_prop)
- src/frob/strata/_ast.py::StoreDecl (new `rpo: Quantity | None` field)
- src/frob/strata/_infra.py::_elaborate_store (rpo dimension validation,
  `rpo=<seconds>` attr; now returns Result)
- src/frob/strata/_infra.py::elaborate_infra (propagates the new Result)
- docs/strata/kernel.md (new "Age propagation semantics" subsection)
- docs/strata/surface.md (store grammar + desugar table updated for `rpo`)
- tests/unit/strata/test_kernel_properties.py (new: hypothesis property
  tests for reachable/worst_age/demand)
- tests/unit/strata/test_infra.py (new: rpo elaboration tests)
- strata-core/src/parse.rs (new cargo test parses_store_rpo)

Evidence: the 14 structured ids in this ticket's evidence list (7 original property/oracle tests + 4 reviewer-round regressions + 3 negative-quantity tests).

Kernel bug found and fixed: `test_worst_age_cycle_property` shrunk to the
single self-loop `('f0', 'n0', 'n0', 0.0)` -- a zero-age self-loop made
`worst_age` return `+inf`, because the old `worst_age_visit` treated ANY
revisited-while-active node as an unbounded cycle, regardless of the
cycle's actual accumulated age. Per docs/strata/kernel.md#age-propagation-
semantics, only a *positive*-age cycle reaching the target should be
unbounded. Fixed by adding a pre-pass (`has_positive_cycle_reaching`) that
DFS-searches for a positive-weight cycle able to reach the target and
returns +inf with the cycle witness only in that case; the memoized DFS
(`worst_age_visit`) no longer special-cases revisits as infinite -- it now
returns `-inf` for a revisit so that branch never wins the max, which
degrades gracefully to a longest-*simple*-path search whenever no positive
cycle exists. The shrunken counterexample is exercised as a regression via
the property test itself (`test_worst_age_cycle_property`), and the
existing `worst_age_is_infinite_on_positive_cycles` / `worst_age_takes_the_
stalest_path` cargo tests continue to pass unchanged, confirming the
positive-cycle and no-cycle behaviors were preserved.

## Reviewer round: soundness fix

The reviewer REJECTED the first pass with a CRITICAL finding: the
memoized-DFS `worst_age` (the fix for the zero-age-self-loop bug above)
was itself unsound. Verified counterexample against the built extension:

```
edges = [("e0","B","A",0.0), ("e1","B","T",0.0), ("e2","A","T",3.0),
         ("e3","A","B",0.0), ("e4","C","B",1.0)]
strata_core.worst_age(edges, "T")  ->  (3.0, [A,e2,T])   -- WRONG
true answer: 4.0 via C->B->A->T
```

Mechanism: `best[node]` was memoized under whichever caller's active-set
happened to compute it first. `A` got memoized as `(0.0, [A])` while `B`
was on the active stack (correctly excluding the `A<-B<-C` continuation
*in that context*), and that truncated cache entry was then wrongly reused
when `A` was visited again with `B` no longer active. An undercount here
is the worst possible bug class for this tool: it can make `bound age(x)
<= v` FALSELY PROVED.

Fix: replaced the memoized-DFS entirely with SCC condensation, per the
reviewer's required design --

1. Kept the positive-cycle pre-pass (`has_positive_cycle_reaching`,
   `find_positive_cycle`) unchanged: with non-negative ages, if any
   positive-weight cycle reaches the target, return `+inf` with a cycle
   witness.
2. Added `_facts.py::_validate_nonnegative_quantities` and
   `StrataError.NegativeQuantity` so `build_facts` fails closed (ERROR-
   logged) on any negative flow age/rate/size -- the surface grammar
   cannot express this, but the Python API can, and non-negativity is the
   premise the SCC argument depends on (documented in
   docs/strata/kernel.md#age-propagation-semantics).
3. Otherwise: compute SCCs (`compute_sccs`, Tarjan, node ids visited in
   sorted order, edges pre-sorted by flow id -- fully deterministic),
   contract each SCC to one supernode, and run standard longest-path DP
   over the condensation DAG in topological order (Kahn's algorithm). This
   is exact and carries no caller-context-dependent state at all.
4. Witness reconstruction (`zero_weight_path`) walks the chosen-edge chain
   from target's SCC back to a root, then BFS-stitches each inter-SCC hop
   through its SCC's zero-weight interior (sound only because step 1/2
   already ruled out positive-weight intra-SCC edges). Verified by hand
   against the reviewer's counterexample (traced in the code review): the
   reconstructed path is exactly `[C, e4, B, e0, A, e2, T]`, age `4.0`.
5. Added the counterexample verbatim as a permanent regression: cargo
   `worst_age_reviewer_regression_context_dependent_memo`
   (strata-core/src/lib.rs) and pytest
   `TestReviewerRegression::test_context_dependent_memo_undercount`
   (calling `strata_core.worst_age` directly), plus three hand-built
   adversarial cases with a node shared across divergent caller contexts
   (`test_adversarial_shared_node_divergent_entry_a/b`,
   `test_adversarial_three_way_convergence`).
6. Closed the generator coverage gap: `_cyclic_edges` now draws ages from
   `[0.0, 0.0, 0.0, 1.0, 2.0]` instead of a uniform float range, so
   zero-net-weight cycles reaching the target actually form during
   property testing (a uniform float draw almost never lands on exactly
   0.0, so this regression class was invisible to the original generator).
7. Documented the non-negativity precondition and the counterexample in
   docs/strata/kernel.md#age-propagation-semantics.

Changed (reviewer round, additive to the list above):
- strata-core/src/lib.rs::worst_age (rewritten: SCC condensation DP,
  replacing the memoized-DFS `worst_age_visit`)
- strata-core/src/lib.rs (new: strongconnect, compute_sccs, zero_weight_path)
- strata-core/src/lib.rs (new cargo test:
  worst_age_reviewer_regression_context_dependent_memo)
- src/frob/strata/_errors.py::StrataError (new NegativeQuantity member)
- src/frob/strata/_facts.py::build_facts (new
  _validate_nonnegative_quantities call)
- src/frob/strata/_facts.py (new: _validate_nonnegative_quantities)
- docs/strata/kernel.md (non-negativity precondition + counterexample)
- tests/unit/strata/test_kernel_properties.py (new: TestReviewerRegression
  class; _cyclic_edges biased toward exact 0.0)
- tests/unit/strata/test_facts.py (new: negative-quantity tests)

Filed: none

Gates: `frob check --ticket T-0065` clean (exit 0; only pre-existing waived
PERF003/frob-exports/frob-arch warnings unrelated to this ticket's scope);
plain `frob check` clean (exit 0). `cargo test` (strata-core) 43/43 green,
including the reviewer's exact counterexample. `make core` rebuilt at repo
root. `uv run pytest tests/unit/strata -q` all green, repeated 3x (property
suite re-run each time with fresh hypothesis examples). ruff format/check
clean. ty clean. `frob graph build` clean. `frob ticket sweep T-0065` run
last before the final `frob check`.
