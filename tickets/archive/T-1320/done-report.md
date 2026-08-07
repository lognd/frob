## Done report

Re-baselined TEST005 against a fresh, honest coverage run in a quiet
window (no concurrent agents, per the OOM lessons).

Path there took three runs. Run 1 exposed six real-repo test
regressions from the drive's own lands (fixed on main under T-1329:
refactor node modeled in design/frob.strata, 11 tickets_ledger SYS104
interface adds, COMPLIANCE007 test locked clean at 0, vet
FP-DESERIALIZE-YAML-001 explicit-Loader refinement). Run 2 exposed the
second-order fallout (export goldens + node count 20->21,
regenerated/updated). Run 3 passed (one xdist worker crash on the
eval-needle test, clean on serial rerun), but `coverage xml` died on a
stale `src/demo/__init__.py` entry in the combined data so
stamp-coverage failed with no coverage.xml -- and make coverage does
NOT propagate a stamp failure (exit 0 despite it; ticket to file).
Recovered by `coverage xml -i` + `frob check --stamp-coverage`:
stamped 837 files, locked 444 modules, source_sha=7a8fcb32.

Re-derivation result for src/frob/app: 85 TEST005 findings, 14 at
0.0% branch -- versus the stale baseline's 115/63. Repo-wide TEST005:
903 warnings, 0 errors -- inside the 700-950 post-attribution-fix
estimate from the drive's diagnosis. T-1276 stays OPEN (real residual
work: 14 true-zero symbols + 71 sub-floor), now unblocked and honest:
its workers read the fresh stamp, not the stale list in its title.
The evidence-only-close precedent (17 tickets across 3 batches)
is vindicated: the phantom findings are gone from the source.

### Changed
(no changed files detected)

### Evidence
- `cmd:uv run --frozen frob check --only test exit=0 sha256=5383529021de` (cmd evidence, exit=0)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 9 error(s), 1274 warning(s), 686 waived
- error-findings: ARCH001@src/frob/gates/_debt_deprecated.py, ARCH001@src/frob/refactor/_scan.py, ARCH001@src/frob/tickets/_land_finalize.py, COV001@design/frob.strata, OPAQUE001@src/frob/app/__init__.py, OPAQUE001@src/frob/app/app.py, PERF003@src/frob/gates/_debt_deprecated.py, RENDER001@src/frob/refactor/_cli.py, TICK003@tickets.md
