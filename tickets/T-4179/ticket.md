---
id: T-4179
title: land --dry-run writes to the worktree, its auto-fix splits a node id inside
  a directive, and the next run refuses the operator for the tool's own edit
state: queued
kind: bug
origin: agent
created: '2026-09-07'
priority: critical
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
acceptance:
- text: given a directive comment whose value would exceed the wrap width, when the
    auto-fix runs, then the value is left unsplit and the directive still resolves
  evidence: []
- text: given a dry run, when it completes, then the worktree is byte-identical to
    how it found it
  evidence: []
- text: given a refusal caused by the tool's own uncommitted edit, when the message
    is printed, then it names the verb that made the change
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
A DRY RUN MUTATED THE WORKTREE, CORRUPTED A DIRECTIVE, AND THEN REFUSED THE NEXT
RUN BECAUSE OF ITS OWN EDIT. Reported as logand.app-v2 F-380. Three defects in
one sequence, and they compound in exactly the wrong order.

WHAT HAPPENED, in their words and order:

  1. `frob ticket land --dry-run` left THREE MODIFIED FILES behind. A dry run
     wrote to the worktree.
  2. The Tier-A auto-fix re-wrapped directive comment lines to a different width,
     and in doing so SPLIT A PYTEST NODE ID ACROSS THE WRAP -- the fragment
     `...resolves_static_impor` followed by `t kind="unit"` on the next line. The
     directive no longer binds the test it names.
  3. The NEXT dry run then refused with an out-of-scope-waiver-deletion error,
     because the re-wrapped waiver counted as an uncommitted deletion outside
     scope. The tool refused the operator for a change the tool itself had made,
     and the message attributed it to them.

EACH IS SERIOUS ON ITS OWN, AND THE MIDDLE ONE IS THE WORST.

A DRY RUN THAT WRITES IS A BROKEN CONTRACT. The whole value of the flag is that
it is safe to run when you are unsure. If it mutates, an operator who used it
precisely to avoid mutating has been misled, and any subsequent measurement of
their tree is measuring the tool's edits as well as their own.

A FORMATTER THAT SPLITS A TOKEN INSIDE A DIRECTIVE VALUE IS SILENT CORRUPTION.
This is not a cosmetic rewrap: a node id broken across a line no longer resolves,
so the binding it expressed is gone while the comment still LOOKS like a
binding. That is the silent-zero shape applied to the comment DSL -- the
directive is present, reads correctly to a human, and does nothing. This queue
has already filed two other instances of exactly that in the DSL: a free-text
symref accepted silently, and a multi-line waiver whose continuation lines lack
the comment prefix failing to attach. This is the third, and the only one where
FROB ITSELF introduces the breakage.

A REFUSAL THAT BLAMES THE OPERATOR FOR THE TOOL'S OWN EDIT is the fourth
refusal-message defect this drive. The reporter's ask is exact and cheap: the
message should say the change is the tool's own.

THIS REPO HAS PRIOR HISTORY WITH TIER-A REWRITES AND IT IS RELEVANT. A pre-land
parse guard once ran BEFORE the Tier-A rewrite it was meant to cover, and three
lands went out before that was noticed. So the ordering of guard-versus-rewrite
here has bitten before; check whether the same inversion explains why a rewrite
that produces an unparseable directive is not caught immediately by the very
guard that should reject it.

WHAT TO DO, in priority order
  1. STOP THE TOKEN SPLIT. A wrapper operating on directive comments must treat a
     directive VALUE as atomic -- a node id, a path, a symref, a waiver reason
     token -- and never introduce a break inside one. If the value cannot fit,
     leave the line long. An over-long line is a lint finding; a split node id is
     a lie.
  2. MAKE THE DRY RUN NON-MUTATING. If the Tier-A fix must run to produce an
     accurate preview, run it against a copy and discard it, or report what it
     WOULD do without applying it.
  3. Attribute the change in the refusal. When the uncommitted diff the tool is
     refusing over was written by the tool, say so and name the verb that wrote
     it.
  4. Check whether the parse guard runs before or after the rewrite, per the
     history above, and fix the ordering if it is inverted.

MUST-FIRE FIXTURE:   a directive comment whose value would exceed the wrap width
                     is left unwrapped rather than split, and the directive still
                     resolves.
MUST-STAY-QUIET:     a dry run leaves the worktree byte-identical to how it found
                     it.
THIRD FIXTURE:       a refusal triggered by the tool's own uncommitted edit names
                     the verb that made it.

ACCEPTANCE
- Directive values treated as atomic by the wrapper; no split can occur inside
  one.
- The dry run proven non-mutating.
- Tool-authored changes attributed in the refusal message.
- The guard-versus-rewrite ordering checked against the prior incident.
- All three fixtures committed.
