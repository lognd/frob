## Done report

New module `src/frob/strata/_atomic.py` (kernel-level engine over
`Module`/`KernelModel`, T-0074 precedent), exported via `__init__.py`:

- `evaluate_saga_contracts(module, model)` -- the cross-store refusal's
  companion obligation. `CrossStoreAtomicity` (T-0069,
  `_elaborate.py::_validate_operations`) already refuses a `modifies {}
  on Err` operation whose `atomic via` spans stores without a declared
  `coordinator`; any operation that survives that refusal legitimately
  declares a saga (docs/strata/boundary.md: "the compensating action is
  retried (at-least-once) and therefore must be idempotent"). This
  module identifies those surviving coordinators, marks every inbound
  flow at-least-once, and re-runs `_facts.py::build_facts` so the
  idempotency finding fires through the SAME diagnostic path used for
  queues and T-0074's crash-retry join -- never a parallel one that could
  drift.
- `generate_fault_injection_cases(module, error_sets)` -- exhaustive
  fault injection (L2, docs/strata/evidence.md): for every operation
  declaring the `modifies {} on Err` strong guarantee, one
  `FaultInjectionCase` per member of the caller-supplied `ErrorSet`
  (complete over the declared error model, per typani `ErrorSet`'s
  closed vocabulary). v0's surface grammar has no construct tying an
  `operation` to the Python `ErrorSet` its fallible dependency raises
  (the same class of gap T-0074 deferred to T-0118 for `on crash`
  durations) -- callers supply `error_sets: Mapping[str, type[ErrorSet]]`
  directly; an eligible operation absent from the mapping is logged and
  skipped, not failed closed, since "no ErrorSet declared" is a coverage
  gap, not a structural fault.
- `evaluate_atomic_contracts(module, model, *, error_sets=None)` -- the
  single joined entry point (module docstring), mirroring
  `evaluate_crash_contracts`'s shape.

Deferred (out of scope, not fixed here): the `saga compensate ... within
t` / `reconciled within t` surface grammar from docs/strata/boundary.md
is not yet parseable -- same strata-core grammar gap as T-0074's `on
crash` durations, tracked under T-0118's pattern (no new ticket filed;
T-0118 already covers "surface grammar work needed to make phase-3
kernel-level engines source-parseable" as a class, and adding a
narrower duplicate would fragment that tracking). The "stage-then-commit
decidable from the Result graph" rung (L5, boundary.md rung 1) requires
connecting strata `operation`s to real Python call graphs via frob's own
dup/graph tooling -- a cross-package integration outside
`src/frob/strata/**`, also deferred to a future ticket under T-0052's
phase-3 tree rather than attempted here.

Changed:
- src/frob/strata/_atomic.py (new)
- src/frob/strata/__init__.py (exports)
- tests/unit/strata/test_atomic.py (new, 9 cases)

Evidence: 9 test node ids recorded via `frob ticket evidence T-0075`
(see `evidence:` above), all in `tests/unit/strata/test_atomic.py`,
covering `evaluate_saga_contracts`, `generate_fault_injection_cases`,
and `evaluate_atomic_contracts`.

Tests: `uv run pytest tests/unit/strata` -- 222 passed (213 baseline +
9 new); zero regressions. (Correction: an earlier draft of this report
mis-stated this as "154 passed (145 baseline + 9 new)" -- that number
came from misreading a `-q` xdist dot-progress tail without the actual
summary line, not from a real 145-test suite at any point; re-measured
directly with `uv run pytest tests/unit/strata` and
`uv run pytest tests/unit/strata --ignore=tests/unit/strata/test_atomic.py`,
giving 222 and 213 respectively.) (`make core` was run once, at session
start, because `strata_core` was not yet built in this worktree and
test collection failed without it -- T-0091/T-0117 precedent.)

Gates: `frob check --json --only gates` reports 111 diagnostics both
before and after this change (this worktree's actual baseline after
merging main's T-0074 commit -- not 134, which was main's count before
this worktree merged forward; verified via `git stash` on the unstaged
diff). Diff of (file, code, message) tuples between before/after is
empty -- zero new or removed diagnostics. `frob check` (repo-wide, no
ticket scope) exits 0. `frob check --ticket T-0075` carries one residual
`SCOPE001` on `tickets.md` (same class as T-0074's, T-0118) and one
`PRE001` (the pre-work sweep recorded by `frob ticket start` predates
this diff's file list and cannot be refreshed once a ticket is
`in-progress` -- `frob ticket start T-0075` now correctly rejects the
transition); both are CLI-mechanics residuals, not code scope creep.
`ruff check`/`ruff format --check` clean on all three changed/new files.

Filed: none (T-0118 already tracks the surface-grammar-gap class this
ticket's deferrals fall under).
