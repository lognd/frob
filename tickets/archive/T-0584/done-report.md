## Done report

Chose the "timeout + partial-sweep-ok ticket state that prework_gate treats
as provisionally clean" option from the ticket's two sketched designs,
rather than making `frob ticket sweep` background-and-poll like `start`.
Reason: the sweep-and-poll approach only relocates the wait -- an agent who
edits scope then needs PRE001 clean before closing still has to poll for
completion, and the CLI dispatch wiring that would background `sweep`
(app/ticket_runner.py) is out of this ticket's declared scope
(src/frob/gates/**, src/frob/tickets/**) anyway. Bounding sweep_ticket
itself with a wall-clock budget and persisting resumable partial state is
fully implementable inside gates/_prework.py and gates/__init__.py: every
existing call site (start's foreground/background paths, the `sweep`
command, land's refresh) gets the fix automatically via the changed
default, no CLI wiring needed, and it directly answers the ticket's stated
failure mode (a full dup+xref scan exceeding the ~90s per-stage foreground
budget on a slow mount).

Design: `PreworkSweep` gained `partial: bool` and `pending_patterns: tuple`.
`sweep_ticket` now takes `budget_seconds` (default 60s, None = unbounded).
The dup scan + graph load still run once, unbounded (they are not
per-pattern and dup's own bounding is a separate concern); the
per-scope-pattern xref loop checks a wall-clock deadline before each
pattern and, on exceeding it, records a partial sweep with the remaining
patterns as `pending_patterns` instead of blocking to completion. A
subsequent `sweep_ticket` call whose current scope digest still matches a
recorded partial sweep resumes from `pending_patterns` rather than
rescanning already-swept patterns. `prework_gate` (PRE001) treats a partial
sweep whose digest matches the ticket's current scope as provisionally
clean (not a violation) -- the catch-22 this closes is specifically that
PRE001 used to demand a fully-completed digest with no partial-ok state,
so a sweep that could never finish in one foreground-budget-sized call
could never satisfy the gate either.

Cut/left as-is: no expiry/staleness cap on how long a ticket can stay
"partial but provisionally clean" -- the ticket's own two sketched options
did not require one, and each `frob ticket sweep` call makes forward
progress (shrinks pending_patterns) rather than looping forever, so an
explicit cap was left out rather than guessed at. If observed to matter in
practice, that is a follow-up, not folded in here.

docs/modules/gates.md needed updating (AFFECT001/COV001 fired on the
changed prework_gate/PreworkSweep/sweep_ticket/DEFAULT_SWEEP_BUDGET_SECONDS
symbols) -- widened the ticket's scope to include that one doc file via
`frob ticket scope T-0584 --add docs/modules/gates.md` rather than silently
touching an out-of-scope file.

Follow-up (post-close, coordinator-flagged TEST016): `frob test`'s mutation
sweep found one surviving mutant at src/frob/gates/_models.py:180 --
negating `PreworkSweep.partial`'s `False` default to `True`. No existing
test constructed a `PreworkSweep` WITHOUT `partial=` and asserted the
default's observable behavior, so the mutant survived. Added
`TestScopePrework::test_prework_sweep_default_partial_is_false_and_treated_as_final`:
constructs a `PreworkSweep` with no `partial=` kwarg and asserts (a)
`.partial is False` and `.pending_patterns == ()` directly, (b) a
record/load round-trip preserves `partial is False`, and (c) `prework_gate`
accepts it with zero violations (the "treated as a complete sweep" half of
the ask). Hand-verified the kill: flipped the default to `True` in
src/frob/gates/_models.py, re-ran the new test alone -- it failed
(`assert sweep.partial is False` no longer holds) -- then reverted; `git
diff main -- src/frob/gates/_models.py` shows only the original T-0584
diff, confirming a byte-identical revert.

### Changed
```
 docs/modules/gates.md      | 36 +++++++++++++++++--
 src/frob/gates/__init__.py | 17 +++++++++
 src/frob/gates/_models.py  | 17 ++++++++-
 src/frob/gates/_prework.py | 86 ++++++++++++++++++++++++++++++++++++++++++----
 tests/test_gates.py        | 72 ++++++++++++++++++++++++++++++++++++++
 tickets.md                 | 84 +++++++++++++++++++++++++++++++++++++++++++-
 6 files changed, 302 insertions(+), 10 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestScopePrework::test_pre001_passes_with_partial_sweep_matching_digest` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestPreworkSweepBounds::test_sweep_ticket_partial_on_budget_exceeded` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestPreworkSweepBounds::test_sweep_ticket_resumes_pending_patterns` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestScopePrework::test_prework_sweep_default_partial_is_false_and_treated_as_final` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
