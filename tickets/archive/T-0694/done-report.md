## Done report

Changed:
- src/frob/arch/_lock_ordering.py (new): interprocedural lock-ordering
  hazard scanner (`_collect_module_locks`, `_collect_function_lock_events`,
  `_reachable_locks`, `_edges_for_function`, `_find_cycle`,
  `_check_lock_ordering_hazards`).
- src/frob/arch/_models.py: added `ArchCategory` members
  `lock-order-cycle`, `lock-identity-unresolved`.
- src/frob/arch/__init__.py: wired `_lock_ordering` into
  `_run_python_checks` (skips test files, matching the sibling
  concurrency-hazard families) plus a docstring paragraph.
- tests/unit/test_arch.py: new `TestLockOrderingHazards` (5 tests).

Evidence: the 5 node ids above; all pass individually
(`pytest tests/unit/test_arch.py -k TestLockOrderingHazards`) and the
full `tests/unit/test_arch.py` suite (249 tests) passes unchanged.
`frob check --ticket T-0694 --only test` (repo-wide pytest via the TEST
gate) passes clean.

Model: reuses `frob.arch._normalized`'s same-module bare-name resolution
convention (`frob.arch._mayraise._build_name_to_func` /
`frob.arch._fallibility`) for interprocedural call resolution, and a
monotonic chaotic-iteration fixpoint over the same-module call graph
(mirroring `frob.arch._mayraise.compute_may_raise`) to propagate each
function's transitively-reachable lock set through same-module callees.
Lock identity is tracked via curated ctor detection
(threading/multiprocessing/anyio/asyncio Lock/RLock/Semaphore/
BoundedSemaphore) at module-level or `self.<attr>` class-level
assignment sites, per the ticket's own framing. Order-pairs are derived
from each function's own with/acquire event sequence (own events + each
call site's callee reachable-lock set, as ordered slots) and a global
directed graph over canonical lock ids is searched for the first
reciprocal (A->B, B->A) pair. Unresolvable-but-lock-shaped usage (e.g. a
lock passed as a parameter) fires `lock-identity-unresolved` (suggestion
tier, one per function) instead of being silently dropped, fail-closed
per the ticket's own framing; a plain `with open(...) as f:` (no
lock-shaped name) fires nothing.

Real-world validation over frob's own `src/frob/` (non-test files, per
the dispatch's ask): 0 `lock-order-cycle` findings, 22
`lock-identity-unresolved` advisories -- all 22 are calls to the
`derived_state_lock(root, exclusive=...)` / `ledger_lock(root)` /
`_land_lock(root)` / `_coverage_lock(root)` factory context managers
(doctor.py, check/__init__.py, mutate/__init__.py, tickets/_land.py,
tickets/__init__.py, tickets/_store.py, testing/_coverage_wait.py). This
is the CORRECT fail-closed outcome, not a bug: these are fcntl-based
advisory FILE locks wrapped in a context-manager FACTORY FUNCTION
(`frob.process._lock.derived_state_lock` et al.), not module/class-level
`threading.Lock`/`RLock`/`Semaphore`/multiprocessing/anyio/asyncio Lock
constructions -- exactly the "lock passed indirectly / non-curated-ctor"
model limit this module's docstring discloses, so this resolver
correctly reports them as unresolved-but-lock-shaped rather than either
silently ignoring them or false-negatively "clearing" them as safe. Did
NOT edit `src/frob/process/_lock.py` (out of this ticket's scope, per
the dispatch instruction) -- the concurrent T-0918 reentrancy work
there, if landed, does not change this scanner's model (it only tracks
threading/multiprocessing/anyio/asyncio-constructed lock OBJECTS, not
fcntl file locks or `derived_state_lock`'s own reentrancy semantics).

Filed: T-0925 (docs: add lock-ordering hazards section to
docs/modules/arch.md, parent T-0694) -- docs/modules/arch.md is outside
T-0694's declared scope (src/frob/arch/**, tests/unit/test_arch.py), so
no `frob:doc` anchor was added on `_check_lock_ordering_hazards`
pointing at a not-yet-existing section (would have failed DOC002); the
follow-up ticket adds the section and the anchor together, matching how
docs/modules/arch.md documents the sibling T-0695/T-0696 families.

Gates: `frob check --ticket T-0694` clean (chunked per the agent
playbook's anti-stall loop) across coverage, docanchor, doclink,
invariant, decisions, drift, waive, place, scope, prework, fmt,
lang_conformance, lang_project_conformance, walk_lint, excludehazard,
render_lint, parse_failures, and test -- 0 errors in every chunk; all
warnings/waivers seen are pre-existing repo debt unrelated to this
ticket's files. `ruff check` and `mypy` on `src/frob/arch/
_lock_ordering.py` are clean (0 findings each).
