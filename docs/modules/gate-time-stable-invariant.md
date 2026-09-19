# Time-stable invariants gate

### INV010 (T-4221)

<!-- frob:describes src/frob/gates/_inv.py::time_stable_gate -->
<!-- frob:describes src/frob/gates/_inv.py::time_stable_offset_s -->
<!-- frob:describes src/frob/gates/_inv.py::TIME_STABLE_OFFSET_ENV -->

`frob.gates._inv` -- `time_stable_gate` (gate name `time_stable`, WARN
severity for a real failure, UNRESOLVED when a sample could not be
measured, waivable). Consumer F-362/H4-1 (T-4166): a check comparing a
committed-artifact-derived value against wall-clock time passes today
and fails tomorrow, and every existing test supplies "now" and the
artifact's own timestamp from the SAME instant -- so the whole class of
"passes today, fails tomorrow" is invisible until it actually rots.

## The grammar: `kind="time-stable" horizon="<N><unit>"`

A `frob:invariant` anchor may declare:

```python
# frob:invariant INV-042 kind="time-stable" horizon="180d"
```

`kind=`/`horizon=` are required TOGETHER (`frob.graph.dsl._attrs_verb_
error_invariant_time_stable`, alongside that verb's existing `no_import=`/
`establishes=` obligation attrs, T-0757's precedent). `kind` is a closed
vocabulary (`"time-stable"` only, so far). `horizon` is a positive
integer followed by one of `d`/`w`/`m`/`y` (days/weeks/30-day months/
365-day years) -- e.g. `horizon="180d"`, `horizon="26w"`, `horizon="1y"`.
No compound/fractional durations (`"1y6m"`, `"1.5y"`) in this first cut.

## The runner: re-execute the bound test with the clock advanced

For each `kind="time-stable"` anchor, `time_stable_gate` re-runs every
pytest-node-id evidence entry on the anchor's own `Invariant` at three
sampled offsets across the declared horizon: 0 (today, the BASELINE),
the horizon's midpoint, and the full horizon. Each run is a real
subprocess (`frob.process._pytest_spawn.resolve_pytest_argv` +
`frob.process._guard.guarded_subprocess_run`, the same one-convention
pytest-spawning discipline `frob.gates._bug_repro`'s BUG002 repro runner
already uses, T-3311) with `FROB_TIME_STABLE_OFFSET_S` set to that
sample's offset in seconds.

The bound test itself is responsible for actually shifting its own
notion of "now" by that offset -- `time_stable_offset_s()` is the one
shared contract: call it wherever the test would otherwise call
`time.time()`/`datetime.now()` for the value it is asserting against.
A test with no time-stable anchor never needs to read it.

## What fires

- If the baseline (offset 0) run does not pass, INV010 has nothing to
  discharge -- the invariant may have a real problem, but a different
  one (INV001 already flags "no standing evidence" for evidence that
  doesn't collect or pass at all). Skipped, not double-reported.
- If the baseline passes but a later sample fails, INV010 fires WARN: a
  wall-clock-dependent predicate that is passing only because every
  sample checked so far used the same instant for "now" and the
  artifact's own timestamp.
- If a sample could not be measured at all (exec disabled, pytest not
  importable, or the subprocess hit its own timeout budget), INV010
  fires UNRESOLVED for that sample -- the T-2391 fail-loudly doctrine
  this repo already applies elsewhere (e.g. ENV001's missing-pyproject
  case): a could-not-run answer is a different claim than "ran and
  found nothing."

Waivable with the standard `frob:waive INV010 reason="..."` directive.

## Rule table entry

| Rule | Gate name | Meaning |
| --- | --- | --- |
| INV010 | time_stable | (warn/unresolved) a `frob:invariant ... kind="time-stable" horizon="..."` anchor's bound test does not still pass once the clock is advanced across the declared horizon -- see "INV010 (T-4221)" above |
