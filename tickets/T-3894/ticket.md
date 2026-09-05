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
body_changes:
- mode: append
  reason: 'owner addition: Result.catch is the exception-to-Result boundary; 93 candidate
    sites measured, kept separate from the @propagate half'
  actor: logan
  at: '2026-09-05'
  old_length: 5143
  new_length: 9390
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



OWNER ADDITION 2026-09-05: "We also have a exception -> result boundary with
Result.catch; refactor where needed."

This is the SECOND half of the typani 0.1.0 adoption and it is a different
transformation from @propagate above. Keep them separate in the work, even
though they land under one ticket.

  @propagate   Result -> early return   (collapses `if x.is_err: return Err(...)`)
  Result.catch exception -> Result      (collapses `try/except: return Err(...)`)

THE API, measured from typani/_propagate.py:

    catching(*exceptions, on_error=Callable[[BaseException], Any]) -> decorator

    "Decorator factory: wrap a whole function in Result.catch semantics.
     Equivalent to calling Result.catch(lambda: func(*a, **kw), *exceptions,
     on_error=on_error) on every call. Supports both sync and async."

Note the sync path delegates to `Result.catch` while the async path inlines an
equivalent try/except -- so `Result.catch` is the primitive and `catching` is
its decorator form. Use whichever fits: `Result.catch` for a single call being
guarded inline, `@catching` for a whole function that is itself the boundary.

DENOMINATOR, measured in frob's src/ on 2026-09-05:

    93 sites where an `except` block is followed within three lines by
    `return Err(...)`

That is the candidate population, not the confirmed one -- the grep is a shape
match and will include some sites that also do real work in the handler.

WHY THIS MATTERS MORE THAN THE @propagate HALF, despite being a seventh the
size. The house rule is that every fallible operation a caller must handle
returns a Result, and exceptions are only for unrecoverable programmer bugs. The
93 sites are where frob CONVERTS one to the other -- they are the boundary the
rule is about. Each hand-written conversion is a chance to get the boundary
subtly wrong, and the two failure modes are ones this repo has already paid for:
  - too broad: a bare `except Exception` swallows a programmer bug and returns
    it as a user-facing Err, hiding a real defect behind a recoverable-looking
    value.
  - too narrow / wrong place: an exception escapes past a boundary that should
    have converted it, and a caller expecting a Result gets a traceback.
`catching(*exceptions, ...)` forces the exception set to be NAMED at the
boundary, which is exactly the discipline a hand-rolled try/except lets you
skip.

WHAT TO DO
  1. Classify the 93. For each: which exceptions are caught, does the handler do
     anything besides constructing the Err (logging, cleanup, context), and is
     the caught set specific or a bare `except Exception`. Report the counts.
     The bare-Exception subset is the interesting one and may be a finding in
     its own right regardless of whether it is refactored.
  2. Convert the sites where the handler ONLY constructs an Err from the
     exception. Those are mechanical and `on_error=` expresses them exactly.
  3. Leave sites whose handler does real work, unless `on_error` can carry it
     honestly. Do not push cleanup or logging into an `on_error` lambda just to
     make a site convertible -- that trades clarity for uniformity.
  4. Where a bare `except Exception` is found at a boundary, decide whether the
     catch set can be narrowed. That is a behaviour change and needs its own
     justification per site; do not narrow silently as part of a refactor.

DO NOT convert a try/except that exists to SUPPRESS rather than to convert --
some of the 93 may be guarding optional behaviour where the Err is discarded.
Those interact with TYP003 (discarded Result) and should be looked at under
T-3849 instead.

ADDITIONAL FIXTURES:
  MUST-FIRE:   an exception type NOT in the declared catch set still propagates
               out of a converted function (proves the set is honoured)
  MUST-STAY-QUIET: each converted site's existing tests pass unchanged
  THIRD:       a converted async boundary behaves the same as its sync twin

ADDITIONAL ACCEPTANCE
- The 93 classified with counts (mechanical / handler-does-work / bare-Exception).
- Only the mechanical subset converted, unless a case is argued individually.
- The bare-Exception population reported even if left alone -- that list is
  worth having regardless of this refactor.
