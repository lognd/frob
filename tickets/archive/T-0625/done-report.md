## Done report

EPIC T-0330 catch-all family (T-0625): module dependency cycle detection.

Resumed orphaned work from a dead session: commit 71c6f85f
("feat(arch): T-0625 add module dependency cycle detection (ARCH1xx)")
plus an uncommitted tickets.md edit were already in the worktree.
Reviewed the code diff critically; `check_module_dependency_cycles` in
`frob.arch._smells` was already complete and correct: it reuses
`frob.lang.extract_imports`/`resolve_local_import` (the same pair
`frob.app.cycle_runner._build_graph` and `_layering.check_layering_
violations` already call) and the existing `frob.cycle.graph.
DependencyGraph`/`find_cycles` (Tarjan's algorithm) -- no second graph
builder or cycle-finder forked, per the ticket's own body. Each
strongly-connected component of size 2+ (or a self-loop) becomes one
`ArchSuggestion` (category `module-dependency-cycle`) with the full
cycle path in its message and the node count in `metric`. No code
changes were needed; the prior session's implementation held up.

### Ledger recovery (the actual orphaned-work gap)
The prior session's uncommitted `tickets.md` edit (state -> in-progress,
scope additions, evidence, Done report) was lost during this session's
`git merge main` -- the ledger merge driver (`frob ticket merge-driver`)
operates on committed blobs only, and that edit had never been
committed. The registered driver also initially pointed at a stale
global `frob` (0.9.0, predating the `merge-driver` subcommand) and
failed silently to a real conflict on the first attempt; reconfigured
`git config merge.frob-ledger.driver` to `uv run frob ticket merge-driver
...` and re-ran the merge, which then spliced cleanly with no other
sibling tickets disturbed.

Recovered the lost ledger state by replaying the original scope-lease
handoff via the CLI rather than hand-editing YAML: released
`src/frob/arch/_smells.py` and `src/frob/arch/_models.py` from T-0624
(`frob ticket scope T-0624 --remove`, both already-committed-work
releases) and re-added `src/frob/arch/_models.py` to T-0625 (`frob
ticket scope T-0625 --add`, extending the shared `ArchCategory` for
`module-dependency-cycle`), then `frob ticket start T-0625` + `frob
ticket sweep T-0625` to restore in-progress state and a clean PRE001
sweep, then `frob ticket evidence T-0625 ...` for both new test ids.

### Out-of-scope discovery filed separately
`gates-security`'s SELFAUDIT001 stage flagged `src/frob/arch/
_logging_checks.py` (T-0622's file, untouched by T-0625, pre-existing
on main since T-0622 landed) for undeclared exec/net/fetch_url
capabilities on the graphlang design node. Filed as T-0910
rather than fixed here (outside T-0625's declared scope).

### Verification
- `make core` (fresh worktree build after merge; native extensions were
  missing).
- `uv run pytest tests/unit/test_arch.py -p no:cacheprovider -n0
  --timeout=300` -- full file, 220 passed (2 new:
  TestModuleDependencyCycles x2, real on-disk import cycles/acyclic
  pairs via `tmp_path`).
- `uv run frob check --only lint --ticket T-0625` -- 0 errors, 0
  warnings.
- `uv run frob check --only static --ticket T-0625` -- 0 errors, 213
  warnings (all pre-existing, unrelated to this ticket's files).
- `uv run frob check --only gates-fast --ticket T-0625` -- 0 errors
  (after the scope-lease recovery above; SCOPE001 failed once on
  `src/frob/arch/_models.py` before the lease was restored).
- `uv run frob check --only gates-native --ticket T-0625` -- 0 errors.
- `uv run frob check --only gates-security --ticket T-0625` -- 0 errors
  in scope (SELFAUDIT001's 5 findings are on the out-of-scope T-0622
  file above, filed as T-0910, not fixed here).
- `git diff main --diff-filter=D --stat` -- empty.

### Cuts disclosed
- No wiring into `analyze_project`/the check pipeline (by design, per
  T-0626's own job, the last ticket in this batch).
- Cross-language cycle detection is out of scope -- reuses `frob.lang.
  extract_imports`, python-only (matching `_layering.check_layering_
  violations`'s own scope).

### Changed
```
 docs/modules/arch.md             | 260 +++++++++++
 src/frob/arch/_fallibility.py    | 399 +++++++++++++++++
 src/frob/arch/_logging_checks.py | 335 +++++++++++++++
 src/frob/arch/_models.py         |  42 ++
 src/frob/arch/_normalized.py     |  12 +-
 src/frob/arch/_smells.py         | 648 ++++++++++++++++++++++++++++
 tests/unit/test_arch.py          | 903 +++++++++++++++++++++++++++++++++++++++
 tickets.md                       | 350 ++++++++++++++-
 8 files changed, 2944 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/unit/test_arch.py::TestModuleDependencyCycles::test_two_file_import_cycle_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestModuleDependencyCycles::test_acyclic_imports_not_flagged` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
