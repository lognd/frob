---
id: T-2230
title: 'T-2193 residue: must_still_pass_violations is not re-exported from frob.gates,
  so a landed call site deep-imports the private submodule'
state: queued
kind: bug
origin: human
created: '2026-08-16'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: Importing must_still_pass_violations from frob.gates (the package) succeeds;
    fails today with ImportError
  evidence: []
- text: The existing five re-exports still resolve unchanged -- must-still-pass control
    against a rewritten import block dropping one
  evidence: []
- text: The landed deep-import call site is updated to the package surface, or an
    explicit reason is given; state which
  evidence: []
- text: No private helper from _mutation_evidence becomes publicly importable as a
    side effect; name the surface before and after
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
---
# T-2193 residue: `must_still_pass_violations` is not re-exported from `frob.gates`, so consumers must deep-import the private submodule

## Measured evidence (2026-08-16)

`src/frob/gates/__init__.py:159` re-exports five names from
`frob.gates._mutation_evidence`:

    from frob.gates._mutation_evidence import (
        BugReproOutcome,
        bug_repro_outcome_at_ref,
        bug_repro_violations,
        designated_repro_test,
        mutation_evidence_violations,
    )

`must_still_pass_violations` -- added by T-2193 (BUG003) and now wired into
both land and close by T-2215 (`bc95220ec44f`) -- is absent. Its direct
siblings in the same module, serving the same gate family, are all present.
This is an asymmetric omission, not a deliberate exclusion: nothing
distinguishes BUG003's entry point from BUG002's.

Consequence, already paid once in landed code: T-2215's agent could not import
it from the package surface and imported it from the private submodule
instead, disclosing the workaround in its Done report as an unfiled gap. So
the package's public surface now understates what the gate family offers, and
one landed call site reaches around it.

## Do NOT fix it this way

- **Do NOT leave the deep import in place and call it fine.** The whole point
  of the `__init__` re-export block is that `_mutation_evidence` is private;
  a consumer importing it directly is coupled to a private module path.
- **Do NOT add a blanket `from frob.gates._mutation_evidence import *`.** That
  would export genuinely private helpers (the module also holds internal
  regexes and parsing helpers) and is a much larger public-surface change than
  this ticket warrants.
- **Do NOT re-export every name in the module "for consistency".** Add the one
  name whose absence is the defect. If you believe others are also missing,
  say which and why, with the consumer that needs them -- do not widen on
  aesthetics.

## Acceptance criteria

1. (MUST FAIL FIRST) A test importing `must_still_pass_violations` from
   `frob.gates` (the package, not the submodule) succeeds. Fails today with
   ImportError.
2. The existing five re-exports still resolve unchanged (must-still-pass
   control) -- a reordered or rewritten import block must not drop one.
3. The landed deep-import call site is updated to use the package surface, OR
   an explicit reason is given for leaving it. State which.
4. No private helper from `_mutation_evidence` becomes publicly importable as
   a side effect. Name what the module exposes before and after.
