## Done report

Shipped CACHE001, the memoize_per_run shape from the ticket's own "detector core, not every
wrapper" acceptance floor.

src/frob/gates/_cache_gate.py: AST-based detector (same structural-gate precedent as
_walk_lint.py/_pii_structural, no vet/effect-scan reuse needed for this narrower shape). For every
@memoize_per_run-decorated function, scans the function's OWN body for Path.read_text/.read_bytes/
open()/os.environ/os.getenv reads whose target expression names none of the function's own
parameters. frob:waive CACHE001 reason="..." is the escape hatch for a genuinely immutable-for-the-
run read.

Registered as a new "cache" gate family (CACHE001 in _KNOWN_GATE_RULES, job table entry in
frob.gates.__init__._build_process_jobs, stage-group membership in gates-security in
frob.check.__init__). Verified clean against the live repo's three real memoize_per_run call sites
(frob.arch.analyze_project, frob.dup._legacy.find_duplicates, frob.graph.build_graph) -- 0 false
positives.

Registry: docs/design/registry/check-coverage.yaml synced via frob registry audit
--sync-gate-rules (CHK-GATE-CACHE001 entry). Docs: docs/modules/gates.md gets a CACHE001 catalog
row plus a "CACHE001 (T-1520)" section.

Land-repair pass (this refresh): the worktree carried a stale merge -- an earlier git merge main
had silently dropped T-1531 via the ledger merge-driver splice; restored per playbook section 10b.
Landing then surfaced three gate-error families against this series' new files:

- COV002: T-1519 (sibling ticket) is done, so its frob:ticket edges no longer cover
  tests/_cache_transparency.py / tests/test_cache_transparency.py as "open" coverage. Widened this
  ticket's scope (frob ticket scope T-1520 --add) to cover both files, and added explicit
  frob:ticket T-1520 edges on tests/test_cache_transparency.py's symbols to break an ambiguous
  scope tie against the T-1529 follow-up draft, which also declares scope over that file.
- SELFAUDIT001 (SYS100/SYS104): design/frob.strata's gates node needed cache_gate added to its
  interface= list and src/frob/gates/_cache_gate.py added to the env/fs.read may-via lists; the
  testsuite node needed the new cache-transparency harness symbols (EDIT_KINDS, Fingerprint,
  TestGraphCacheTransparency, TestPytestCollectCacheTransparency, TestMemoizedReadCoverage,
  TestT1454RegressionShape, git_init, git_commit_all, run_cold_warm_sweep) added to its interface=
  list and the exec/fs.write/fs.read/env capabilities their new test files use declared via-lists.
  This file carries two duplicate attr interface=/may blocks per node (pre-existing repo structure,
  not introduced here) -- updated both identically.
- WIRE001: test-only fixture helpers (git_init, git_commit_all, run_cold_warm_sweep,
  _git_init_tracked, _graph_fingerprint) waived per the repo's established test-fixture-helper
  precedent (follow_up=T-1490, verbatim idiom from tests/test_tickets_migration.py -- WIRE001's
  reachability scan skips all test paths by design, so a helper reached only from other test files
  always reads as unwired). cache_gate itself waived with a NEW follow-up ticket
  (T-1532, renumbers at land): it is genuinely wired via a bare first-class function
  reference inside _ProcessJob(cache_gate, (st.repo_root,)) in the process job table, a shape
  WIRE001's call-shaped text scan cannot see -- distinct from T-1502 (memoize_per_run wrapper
  bare-name argument) and T-1527 (ErrorSet no-paren member access).

Verification: FROB_NO_GATE_CACHE=1 uv run frob check --only coverage --only sys --only wire --only dup
--path . -> 0 errors (COV 0/32w/144waived, SELFAUDIT 0, WIRE 0/6waived, dup 372 groups/1 waived).
FROB_NO_GATE_CACHE=1 uv run frob check --only cache --only archgate --path . -> 0 errors.
pytest tests/test_cache_transparency.py tests/test_gate_cache.py tests/test_cache_gate.py -> 22 passed.

### Changed
```
## Done report

The T-1514 pre-commit unscoped sweep compared staged-tree findings against the pre-land baseline with no allowance for the files the land machinery itself rewrites at that checkpoint. A land needing a REL001 version bump stages .frob-release.json/CHANGELOG.md/pyproject.toml changes; PRE001/SCOPE001 then fired against them as new-vs-baseline and refused the land (observed blocking T-1517 twice on 2026-08-04, while non-bumping lands passed). Fix: _LAND_OWNED_SWEEP_EXEMPT + _is_land_owned_finding filter exclusions from both the initial comparison and the post-Tier-A re-check, logged loudly per the no-silent-caps rule; matching is restricted to repo-root paths so a nested pyproject.toml in a fixture tree still refuses. Two unit tests cover the exemption and the nested-name boundary.

### Changed
```
## Done report

frob ticket list now always ends with a one-line state census (summary: N active (X queued, Y in-progress, ...)) computed from the queue the list already loaded -- zero extra IO -- replacing the 'list | grep queued | wc -l' shell idiom. A new --stats flag appends a second line with trailing-3-day filed/landed/net rates, median created-to-first-done cycle time, and the naive burn-down ETA, all off the existing T-1100 ticket_flow report; TicketFlowReport gained median_cycle_days, mined in the same single git-history pass _count_landed_by_day already makes (no second walk). The help text discloses --stats inherits frob ticket flow's full-history mining cost until T-1330 lands. User-requested 2026-08-04.

### Changed

### Changed
```
 design/frob.strata                       |  48 +++---
 docs/design/registry/check-coverage.yaml |   6 +-
 docs/modules/gates.md                    |  51 ++++++
 frob.lock                                |  10 ++
 invariants/INV-050.md                    |  69 ++++++++
 src/frob/check/__init__.py               |   1 +
 src/frob/gates/__init__.py               |  14 ++
 src/frob/gates/_cache_gate.py            | 271 +++++++++++++++++++++++++++++++
 src/frob/gates/_gate_cache.py            |   3 +
 src/frob/gates/_waive.py                 |   6 +
 src/frob/graph/cache.py                  |   3 +
 src/frob/tickets/_store.py               |   3 +
 tests/_cache_transparency.py             | 113 +++++++++++++
 tests/test_cache_gate.py                 | 132 +++++++++++++++
 tests/test_cache_transparency.py         | 155 ++++++++++++++++++
 tests/test_gate_cache.py                 |  17 +-
 tickets.md                               | 202 +++++++++++++++++------
 17 files changed, 1019 insertions(+), 85 deletions(-)
```

### Evidence
- `tests/test_cache_gate.py::TestMemoizedReadCoverage::test_uncovered_read_fires` (pytest node id, verified passing when recorded)
- `tests/test_cache_gate.py::TestT1454RegressionShape::test_env_read_fires` (pytest node id, verified passing when recorded)
- `tests/test_cache_gate.py::TestMemoizedReadCoverage::test_silent_shapes[param-derived-read]` (pytest node id, verified passing when recorded)
- `tests/test_cache_gate.py::TestMemoizedReadCoverage::test_silent_shapes[non-memoized-function]` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
