# RACE001/RACE002: concurrent read-then-write test obligation (T-3953)

Standalone page -- `docs/modules/gates.md` is leased by T-3259 and
T-draft-a62505d4 for this ticket's entire duration (the same lease-conflict
shape T-4605's own body already tracks for T-4114/T-4115/T-4221/T-3962/
T-3961). Once `docs/modules/gates.md` is free: fold this section into it
next to the other `INV0*` rule-catalog rows and delete this file; a
fold-in item has been appended to T-4605's body so the fold happens the
same way every other lease-blocked gates.md doc addition has.

## Problem (F-181, T-3942 item 7)

T-3919/T-3942's delta audits kept re-finding the same un-tracked shape: a
function reads a value keyed by something (a dict lookup, a `.get(key)`
call), then later writes a NEW value back to the same key, derived from
that read -- with no lock, Lua/atomic script, INCR-style single-op update,
or conditional UPDATE guarding the two operations. Two concurrent callers
racing this read-check-write can silently lose an update. The same audit
also named a related, cheaper-to-check gap one layer up: a docstring or
spec claiming cap/quota/single-use/idempotent behavior with NO test that
actually calls the function from concurrent callers -- the claim has
never been put under the one condition that would break it.

T-3919/T-3942's own explicit caveat: this is a heuristic shape and will
be waived into uselessness fast if pitched as a hard-error gate -- ship
as `Severity.WARN`, and bias every detection decision toward silence over
a false claim (see each helper's own guard-detection doctrine below).

## Fix: `race001_violations` (`frob.gates._inv`)

Walks every Python function symbol in the graph snapshot, resolving each
`path::qualname` symref to its real AST node, and runs two independent
checks against it:

- **RACE001** (`_race001_function_violation`): collects every `tmp = BASE
  [KEY]` / `tmp = BASE.get(KEY, ...)` read (temp variable -> `base::key`),
  then every `BASE[KEY] = rhs` / `BASE[KEY] += rhs` write in the same
  function; fires if some write's `base::key` matches an earlier read's,
  AND the write's RHS expression references the read's temp variable
  (`rhs` genuinely derived from the read, not an unrelated overwrite) --
  UNLESS `_race001_guard_present` finds ANY call or `with`-target anywhere
  in the function whose name matches `lock|acquire|incr|watch|multi|
  pipeline|eval|atomic|transaction|cas` (case-insensitive). That guard
  check is deliberately generous: a false negative here just means
  RACE001 stays silent on an already-safe function, never a false claim
  on a genuinely guarded one.
- **RACE002** (`_race002_test_obligation_violation`): fires when the
  function's own docstring matches `\b(cap|quota|single-use|idempotent)\b`
  (case-insensitive) AND it has at least one `frob:tests` binding AND NONE
  of those bindings' pytest node id or resolved test source matches
  `concurrent|thread|race|parallel` (case-insensitive). A symbol with NO
  `frob:tests` bindings at all is silent here -- that is COV002's
  territory (untested symbol), not this rule's; RACE002 only fires once
  there is SOME test but it never exercises concurrent callers.

## Positive controls

- An unlocked `STORE.get(key, 0)` read followed by a derived `STORE[key]
  = ...` write fires RACE001
  (`tests/gates_suite/test_invariant.py::TestRace001Violations.
  test_fires_on_unlocked_read_then_write_same_key`).
- The identical shape wrapped in `with _LOCK:` is silent
  (`tests/gates_suite/test_invariant.py::TestRace001Violations.
  test_silent_when_a_lock_guards_the_read_then_write`).
- A read of one key and a write to a DIFFERENT key is silent (not the
  same-key race this rule is about)
  (`tests/gates_suite/test_invariant.py::TestRace001Violations.
  test_silent_when_read_and_write_target_different_keys`).
- A docstring claiming "single-use" cap behavior, bound only to a
  single-caller test, fires RACE002
  (`tests/gates_suite/test_invariant.py::TestRace001Violations.
  test_test_obligation_fires_with_no_concurrent_binding_test`); the same
  docstring bound to a test named `test_bump_concurrently` is silent
  (`tests/gates_suite/test_invariant.py::TestRace001Violations.
  test_test_obligation_satisfied_by_a_concurrent_binding_test`).

## Known scope limit (out of this ticket's scope: `src/frob/gates/_inv.py` only)

`race001_violations` is implemented and tested standalone; wiring it into
`frob check`'s actual job list (`frob.gates.__init__._build_jobs`, plus
the rule-severity table and `design/frob.strata`/`docs/design/registry/
check-coverage.yaml` entries) requires editing `src/frob/gates/__init__.py`
-- the same lease-blocked wiring step T-3997/TESTMOCK001 hit (its gate
page lands with T-3997). T-4647 already tracks TESTMOCK001's
wiring against `src/frob/gates/__init__.py`; this rule's own wiring can
land in the same follow-up pass once that file's lease clears (noted here
rather than filing a near-duplicate ticket).
