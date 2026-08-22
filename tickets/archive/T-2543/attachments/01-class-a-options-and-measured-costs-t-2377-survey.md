# T-2543 Class A: the subscript `KeyError` default -- options and costs

PROPOSAL ONLY. No option below is implemented; this exists so the call
is made with numbers in front of it rather than discovered in the floor.

## Measurement basis

All counts are `frob check --only exhaustive_handling`, unbudgeted, with
`FROB_NO_GATE_CACHE=1`, taken on `main` AFTER T-2539 and T-2552 landed.

  Baseline today:  EXHAUST002 = 47, EXHAUST003 = 141

41 of the 47 name `KeyError`. Every one of those traces to
`_resolve_call_contributions`'s `_SUBSCRIPT_RAISE` rule, which gives any
non-slice subscript the curated dict-index default.

## What the corpus actually indexes

For each of the 41, walking the function and its transitive same-module
callees and classifying every non-slice subscript's KEY expression:

  30 of 41  reach an integer-literal index   -> sequence, so the true
                                                risk is IndexError
   9 of 41  reach a string-literal key       -> mapping, KeyError is right
  35 of 41  reach a computed key             -> shape genuinely unknown

Taken as whole findings rather than sites:

   5  reach ONLY integer-literal indexes  -> `KeyError` is simply the
                                             wrong type name
   1  reaches ONLY a string-literal key   -> `KeyError` is correct
  35  reach a mix, or a computed key      -> undecidable without types

So "the model names the wrong type" is well supported in aggregate (30
of 41 touch sequence indexing) but only 5 findings are PURELY sequence.
Shape inference would rename many and resolve few.

## Options, each with its measured cost

  A1  Drop the subscript contribution entirely.
      EXHAUST002 47 -> 8.
      Cost: unsound. Deletes the entire unhandled-lookup class, not just
      its false positives. The 6 findings that genuinely index a mapping
      go silent with the rest. Cheapest number, worst gate.

  A2  Model an ambiguous subscript as `LookupError`, `_catches`
      unchanged.
      EXHAUST002 47 -> 47.
      NOTE, AND THIS CORRECTS MY OWN EARLIER CLAIM: I reported that A2
      would be "strictly noisier" because `except KeyError:` does not
      discharge a raised `LookupError`. Measured, it is not -- the count
      is identical, because the flagged sites are flagged precisely
      BECAUSE they catch neither. The predicted noise lands on sites that
      already pass, so it never materialises. A2 costs nothing and names
      the type honestly ("a lookup may fail" is exactly what the model
      knows). `_EXCEPTION_PARENT` already maps both `KeyError` and
      `IndexError` to `LookupError`, so no map change is needed.

  A3  A2 plus a relaxation: an ambiguous parent is discharged by
      catching any of its children.
      EXHAUST002 47 -> 42.
      Cost: a real soundness relaxation, for 5 findings. It also lets
      `except KeyError:` discharge a genuine IndexError path, which is
      the same class of miss the current default already causes in the
      other direction. Poor value.

  A4  Keep the rule, split subscript-derived findings into their own
      quieter code (an EXHAUST004), exactly as T-1402 split EXHAUST003
      out of EXHAUST001 for the unresolved-callee case.
      EXHAUST002 47 -> 8; new code carries 39.
      Cost: no soundness change at all. The signal is preserved and
      still reported; only its confidence tier changes. This is the one
      option that lets EXHAUST002 be promoted to ERROR without either
      deleting a real class or annotating 39 sites.

  A5  Infer receiver shape (a name bound from `.splitlines()`/`.split()`
      /`list(...)`, or a `list[...]`/`Sequence[...]` annotation) and pick
      `IndexError` there, `KeyError` for a mapping, `LookupError`
      otherwise.
      Expected: resolves ~5 findings outright, renames ~30.
      Cost: real local type inference the model does not have today --
      `NormalizedFunction` carries no local assignments at all, so this
      needs a model extension before a single rule can be written. High
      effort, low finding-count return. Correct in the long run; wrong
      thing to do first.

## Recommendation, for the coordinator to accept or reject

A2 + A4, in that order, and NOT A3 or A5 yet.

A2 is free and makes the message honest. A4 is the option that actually
unblocks T-2377's promotion, and it follows a precedent this exact gate
family already set once (T-1402) rather than inventing a new posture. A5
stays filed as the long-run fix, sequenced after the model can express
local bindings.

The residual after A2 + A4 is 8 EXHAUST002 findings -- small enough to
triage by hand, which is the point.

## The residual 8, for planning

Of the 8, 7 name `ValueError` and 1 names `KeyError`. The 7 are a THIRD
false-positive class this survey did not fix and did not file separately:
a guard predicate that establishes the call's precondition. Measured, 10
of the 11 pre-T-2552 residual findings carried one -- `if not
entry.name.isdigit(): continue` immediately before `int(entry.name)`
(the `/proc` pid walks in `_leases.py`, `_reap.py`, `fleet_status.py`),
or a `\d+` regex group feeding `int(match.group(1))`. The resolver has
no notion that a predicate narrows a later call, so it reports
`ValueError` at sites where the source has already excluded it. Worth
its own ticket once Class A is settled; it is the same shape as Class B
(an impossible path demanded) but needs guard-to-call flow, not a table
edit.
