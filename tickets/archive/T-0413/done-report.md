## Done report

Closed the PERF META-GAP: PERF001-006 all reason about one function body
at a time, so none could ever have caught the class of waste that
actually dominated a real `frob check` run here -- the same expensive
computation called repeatedly across different stages with no shared
cache (T-0423's run-scoped memoization fixed the one concrete incident;
this ticket is the enforcement so a NEW instance is caught statically).

Added PERF007 (`frob.perf._redundancy.redundant_computation_violations`,
wired into `perf_rules` in `src/frob/perf/_rules.py`): a
`frob.toml`-configured `[[perf.heavy]]` call target (`name` + optional
`cached_by` decorator names, default `memoize_per_run`/`lru_cache`/
`cache`) invoked from 2+ distinct top-level FUNCTION/METHOD symbols with
none of `cached_by`'s decorators on its own definition fires an error
naming both the redundant call site and the first one it duplicates. No
`[[perf.heavy]]` entries at all means zero PERF007 checking -- fail-open,
matching every other config-driven source in this codebase (DOC004's
namespace/command sources).

Wiring stayed additive: `perf_rules` (fully in scope, `src/frob/perf/
_rules.py`) now also calls `redundant_computation_violations`, so
`gates.py::perf_gate` (out of my declared scope, coverage-family agent's
territory) needed zero changes -- the only `src/frob/gates/__init__.py`
touch is the single additive line registering "PERF007" in
`_KNOWN_GATE_RULES` (so `frob:waive PERF007 reason="..."` is a real,
matchable waiver channel, WAIVE002's own contract).

Acceptance verified exactly per the ticket's wording: a fixture where two
top-level functions both call an uncached configured target is flagged; a
fixture where only one calls it, or the target carries
`@memoize_per_run`, is not; no `[[perf.heavy]]` config at all means zero
checking. Four tests in `tests/test_perf.py::TestPerf007RedundantComputation`
cover exactly these four cases (see Evidence).

### Caveats
- REL001 (`pyproject.toml`'s public-API-vs-version-stamp check) now fires
  repo-wide because `frob.perf`'s `__all__` gained
  `redundant_computation_violations` -- a real, correct consequence of
  this ticket's public API addition, but `pyproject.toml`/the release
  stamp are NOT in T-0413's declared scope and multiple parallel
  worktrees are adding public API in this same window, so bumping the
  version here would race every sibling ticket's own API addition.
  Leaving the version stamp as a land-time/coordinator concern (same
  posture the T-0418/T-0423 Done reports already used), not silently
  worked around.
- `frob check --ticket T-0413` alone shows 3 SCOPE001 findings
  (`docs/modules/gates.md`, `frob.toml`, `tests/test_gates.py`) -- those
  are T-0443's own already-closed, already-scoped files, present in this
  worktree's cumulative diff because both tickets were worked
  sequentially in one worktree; `frob check --delta` (no single-ticket
  scope filter) shows zero SCOPE001, confirming this is a --ticket-scoped
  view artifact of the two-tickets-in-one-diff shape, not a real
  violation.

### Changed
```
 docs/modules/gates.md        |  35 +++++--
 docs/modules/perf.md         |  66 +++++++++++-
 frob.toml                    |  12 +++
 src/frob/gates/__init__.py   |   1 +
 src/frob/gates/_docblocks.py | 239 +++++++++++++++++++++++++++++++++++++++--
 src/frob/perf/__init__.py    |  10 +-
 src/frob/perf/_redundancy.py | 245 +++++++++++++++++++++++++++++++++++++++++++
 src/frob/perf/_rules.py      |  10 +-
 tests/test_gates.py          | 104 ++++++++++++++++++
 tests/test_perf.py           | 115 +++++++++++++++++++-
 tickets.md                   | 236 +++++++++++++----------------------------
 11 files changed, 887 insertions(+), 186 deletions(-)
```

### Evidence
- `tests/test_perf.py::TestPerf007RedundantComputation::test_two_stages_calling_the_same_uncached_parse_is_flagged` (pytest node id, verified passing when recorded)
- `tests/test_perf.py::TestPerf007RedundantComputation::test_single_shared_call_site_is_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_perf.py::TestPerf007RedundantComputation::test_cached_definition_suppresses_the_warning` (pytest node id, verified passing when recorded)
- `tests/test_perf.py::TestPerf007RedundantComputation::test_no_config_means_no_perf007_checking` (pytest node id, verified passing when recorded)
