---
name: prove
description: Dispatch the prover agent until frob check --only invariant reports zero INV violations. Use to drive invariant coverage (frob:invariant anchors and invariants/ entries) to fully evidenced.
---

# prove

Drive the invariant gates to clean. This skill is a loop around the
`prover` agent, not a place to write proofs directly.

## Step 1: Baseline

```bash
frob check --only invariant           # current INV001/INV002 violations
```

If this is already clean, stop -- nothing to do. Report that explicitly
rather than dispatching anything.

## Step 2: Dispatch prover

Dispatch the `prover` agent with the current violation list. It anchors
missing `frob:invariant` comments, writes property tests or policy rules
as evidence, and binds them via `frob:tests` and the invariant's evidence
list.

If the violation count is large, it's fine to dispatch prover once and let
it work through the whole list in one mission rather than one-per-invariant
-- unlike the auditors, there's no boundary-isolation reason to split it.

## Step 3: Re-check

```bash
frob check --only invariant
```

If violations remain, read what's left:

- Still INV002 (no anchor) on the same id -- prover couldn't find an
  enforcing site. Check whether it filed a ticket for missing enforcement
  (its contract requires this); if not, that's a problem with the mission,
  re-dispatch with the specific id called out.
- Still INV001 (no evidence) -- check whether a ticket was filed instead
  (prover defers to `implementer` when the fix is production code, not
  proof). That ticket must exist and be visible in `frob ticket list`.

## Step 4: Loop until clean or genuinely blocked

Repeat Steps 2-3. Stop when either:

- `frob check --only invariant` is clean, or
- every remaining violation has a ticket filed against it (blocked on
  implementation, not on proof) -- in which case this skill's job is done
  and the remainder belongs to `next`.

Do not loop indefinitely against the same unresolved id -- two prover
passes with no progress on a specific `INV-###` means surface it to the
human instead of a third dispatch.

## Output

```
Invariant sweep: N violations at baseline -> M remaining

Closed: INV-007, INV-009 (evidence added)
Blocked on implementation: INV-012 (ticket T-0055 filed, missing enforcement)
Still open, needs human input: INV-014 (two prover passes made no progress)
```

## Hard rules

- Never write production/enforcement code in this skill or ask prover to --
  that's `implementer`'s job once a ticket exists.
- Never mark an invariant closed by weakening its `statement`.
- Never accept an assert-free test as evidence; if prover reports one,
  reject it and re-dispatch.
