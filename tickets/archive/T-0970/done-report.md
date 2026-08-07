## Done report

Changed:
- src/frob/app/check_runner.py -- `_run_stamp_baseline` extraction:
  `_run_baseline_chunks` (new)
- src/frob/arch/_layering.py -- `check_layering_violations` extraction:
  `_layering_violations_for_file` (new); `check_no_di_construction`
  dedup: `_append_no_di_findings` (new)
- src/frob/arch/_concurrency.py -- `frob:waive ARCH001` on
  `_check_pool_inside_pool`
- src/frob/arch/_fallibility.py -- `frob:waive ARCH001` on
  `check_over_broad_except`
- src/frob/graph/summary.py -- `frob:waive ARCH001` on `_tarjan_sccs`
- docs/audits/gates-quality.md -- new "T-0970" section: ARCH001
  burn-down status + the ARCH101/ARCH102/ARCH103 promote-or-advisory
  decision (finding 4's "fresh design decision")

Evidence: tests/unit/test_arch.py::TestLayeringViolations (3 tests),
tests/unit/test_arch.py::TestNoDiConstructionSmell (3 tests),
tests/unit/test_arch.py::TestOverBroadExcept (3 tests),
tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_baseline_mode_calls_stamp_and_returns,
tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_baseline_gate_error_exits_1,
tests/unit/test_arch.py::TestProtocolSummaryEngine::test_recursive_cluster_converges_to_hand_computed_fixpoint
(all bound via `frob ticket evidence T-0970`).

Measured (chunked `frob check --only gates-native --json`, post-`main`-merge):
101 unwaived warnings total across the 4 gated ARCH codes (ARCH001=52,
ARCH101=2, ARCH102=23, ARCH103=24), 13 waived -- the ticket's "101"
figure (from T-0399) is this sum, not ARCH001 alone.

ARCH001 burn-down (partial, 5 of 52 addressed): 3 real extractions that
drop the function below threshold entirely (no waiver needed) --
`_run_stamp_baseline`, `check_layering_violations`,
`check_no_di_construction`'s duplicated loops merged into one shared
helper (also removes real duplication) -- plus 3 honest, specific
`frob:waive ARCH001` additions (`_check_pool_inside_pool`,
`check_over_broad_except`, `_tarjan_sccs`). Post-fix measured: ARCH001
47 unwaived, 16 waived (was 52/13). 47 remain -- too large to finish in
this pass; carried forward whole (exact list captured verbatim) as
remainder child `T-0976`. `[gates.severity] ARCH001` stays at
default (WARN) in frob.toml -- flipping to error with 47 live findings
would red main, which this ticket's own instructions rule out; promotion
is the remainder child's last step once ARCH001 nears zero.

Category decision (the "decide" half, ARCH101/102/103), written into
docs/audits/gates-quality.md's new "T-0970" section: ARCH101
(low-cohesion-class/LCOM4) -- promotable-after-burn-down, small (2 live
findings), near-term; ARCH102 (god-module/export-clustering) -- stays
advisory-only, the clustering heuristic itself hasn't been audited for
the same gameable-heuristic blind spot finding 4 found in the old
god-class scan, promoting an unaudited heuristic risks the same
green-!=-good failure; ARCH103 (mixed-concern-function) --
promotable-after-burn-down, same treatment as ARCH001. Burn-down +
heuristic check for all three tracked in a new child, `T-0977`.

Out-of-scope finding filed, not fixed: `T-0975` --
tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_baseline_only_chunk_records_without_stamping
fails on a stale expected gate set (`exhaustive_handling` missing from
the asserted frozenset) -- pre-existing drift from main's gate
registration moving since this test was last updated, unrelated to any
T-0970 edit (the assertion covers `_resolve_baseline_only_chunk`, which
T-0970 did not touch).

Test evidence: `uv run pytest tests/unit/test_arch.py
tests/unit/test_app_runners_batch6.py -p no:cacheprovider` -> 304
passed, 1 failed (the pre-existing drift above, filed as
T-0975, not caused by this ticket). Targeted reruns after each
edit (`-k Layering`, `-k NoDi`, `-k Tarjan`/recursive-cluster) all green.

`git diff main --diff-filter=D --stat` is empty (deletion-filter check
clean).

Filed: T-0976 (ARCH001 remainder, 47 findings),
T-0977 (ARCH101/102/103 burn-down + heuristic-soundness
check), T-0975 (stale gate-set test drift, out of scope)

Gates: `frob check --only gates-native` measured clean of new errors
(0 errors both before and after); `[gates.severity] ARCH001` intentionally
left unpromoted per the reasoning above -- not a waived gate, a deliberate
not-yet-promoted decision recorded in docs/audits/gates-quality.md.
