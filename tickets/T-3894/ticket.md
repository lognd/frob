---
id: T-3894
title: raise the typani floor to 0.1.0 and refactor the 649 explicit propagate sites
  onto @propagate where the error passes through unchanged
state: queued
kind: feature
origin: human
created: '2026-09-05'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
OWNER DIRECTIVE 2026-09-05: "typani 0.1.0 is cut with typani.lint, and there's
new functionality like @propagate that will make your life easier (refactor
please)."

MEASURED 2026-09-05:
  - PyPI latest for typani is 0.1.0 (releases: 0.0.1 .. 0.0.4, 0.1.0).
  - frob's installed typani is 0.0.3; frob pins `typani>=0.0.3`.
  - So step zero is raising the floor to `typani>=0.1.0`. That also unblocks
    T-3849, whose lint stage needs the `typani.lint` module that ships in 0.1.0.

WHAT @propagate DOES, from its own docstring in typani/_propagate.py:

    Rewrite an ``unwrap()``-raised UnwrapError into a returned container.
    Decorate a function that calls ``.unwrap()`` on a Result or Option; on
    failure the offending container is returned from *func* instead of the
    exception escaping, giving Rust ``?`` / Zig ``try`` style early return.
    Works on plain functions, bound/unbound methods, and the inner function of
    a @classmethod. Any exception other than UnwrapError passes through
    unchanged.

So this collapses the dominant shape in frob's source:

    r = do_thing()
    if r.is_err:
        return Err(r.danger_err)
    value = r.danger_ok

into

    @propagate
    def f() -> Result[T, E]:
        value = do_thing().unwrap()

THE DENOMINATOR: typani's own lint counted 649 instances of
`if x.is_err: return Err(x.danger_err)` (TYP004) in frob's src/.

A NOTE ON A REVERSED JUDGEMENT, recorded so it does not read as inconsistency.
When that count first surfaced I wrote, in T-3849, "do NOT mass-rewrite it --
that is the idiomatic propagate in this codebase and 649 is a measure of Result
adoption, not debt." That was correct then: no alternative existed, so the
pattern was the best available expression. @propagate is new information and it
changes the answer. The count is now a refactor denominator.

BUT DO NOT BLANKET-REWRITE ALL 649. Three constraints make a mechanical sweep
wrong, and each needs a decision:

  1. ERROR IDENTITY. `return Err(r.danger_err)` constructs a NEW container
     carrying the same error. @propagate returns THE ORIGINAL container. Those
     are equivalent only where the error passes through unchanged. Any site that
     MAPS or WRAPS the error (E1 -> E2, adding context, changing the error type)
     is NOT a @propagate site and must keep its explicit form. Classify the 649
     on this axis first and report the split; that number decides the real scope
     of this ticket.

  2. DYNAMIC-EXTENT HAZARD, and this is the one I would most like verified
     before a wide rollout. @propagate catches UnwrapError raised ANYWHERE in
     the dynamic extent of the decorated call, not only from `.unwrap()` calls
     written in that function's own body. An UNdecorated helper that unwraps and
     lets UnwrapError escape would have ITS container returned by the outer
     decorated function -- wrong provenance, and possibly a container whose
     error type does not match the outer signature. Determine empirically
     whether this is reachable in frob's call shapes, and if so, what discipline
     prevents it (decorate consistently? never let UnwrapError cross a module
     boundary undecorated?). State the rule.

  3. LOGGING AND VISIBILITY. This repo's standing rule is to log every
     meaningful branch and error path. The explicit form gives a natural place
     to log at the propagation point; @propagate makes propagation invisible.
     Decide where that is acceptable -- probably fine for pure plumbing, less
     fine at subsystem boundaries where a propagated error is the thing worth
     recording. Do not silently delete logging while collapsing a branch.

ALSO MEASURE, do not assume: the performance cost. @propagate wraps every call
in try/except and frob has PERF gates plus hot paths (the graph builder, the
parser, the gate loop). Measure a hot-path site before and after; if the cost is
real, that alone scopes the refactor away from those paths.

SEQUENCING. Raise the floor to 0.1.0 FIRST and land that alone -- it is a
one-line change that unblocks T-3849's lint stage, and the lint is what will
verify this refactor did not change semantics. Refactor second, in slices, with
the lint running.

DO NOT do this as one enormous commit. Slice by subsystem, and after each slice
confirm the touched code's tests still pass and TYP003 (discarded Result) has
not grown -- a refactor that turns an explicit propagate into a swallowed
container would be caught exactly there.

MUST-FIRE FIXTURES:
  - a decorated function whose inner unwrap fails returns the container, and a
    test asserts WHICH container (guards against the dynamic-extent hazard)
  - an error-MAPPING site still behaves as before (it must not have been
    converted)
MUST-STAY-QUIET:
  - every converted site's existing tests pass unchanged

ACCEPTANCE
- Floor raised to typani>=0.1.0 and landed separately first.
- The 649 classified: pass-through vs mapping vs logging-at-boundary, with
  counts.
- The dynamic-extent hazard investigated and a stated discipline.
- Hot-path performance measured before any hot-path conversion.
- Refactor landed in slices, each verified.
