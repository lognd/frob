---
id: T-4807
title: 'Docstring half of the DOCARCH002 Tier-A --fix: keep paragraph 1, route the
  remainder to the cited ticket or to docs/modules with a frob:doc pointer (1055 docstrings,
  39k lines)'
state: queued
kind: feature
origin: human
created: '2026-09-19'
priority: high
blocked_by:
- T-4694
parent: T-4691
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/narrative
- src/frob/gates/_fix_engine.py
- docs/modules/docstrings.md
- tests/narrative
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given a fixture with a long docstring citing a ticket, when frob check --fix
    runs, then paragraph 1 remains as the docstring and the remainder is appended
    to that ticket body
  evidence: []
- text: given a fixture with a long docstring citing NO ticket, when --fix runs, then
    the remainder is appended to docs/modules/<module>.md under a heading named for
    the symbol and a frob:doc pointer is left on the symbol
  evidence: []
- text: given a docstring citing a T-#### that does not exist, when --fix runs, then
    that one fix REFUSES and is reported -- the prose is never dropped and the ticket
    is never invented
  evidence: []
- text: given the fixture after one --fix, when --fix runs a second time, then neither
    the source nor either destination changes (idempotency)
  evidence: []
- text: given the COV and TEST finding sets before the fix, when the fix has run repo-wide,
    then the finding sets are byte-for-byte identical -- the enforcement surface did
    not move
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Split out of T-4694 per the owner's decision on the docstring half: AUTOMATE IT,
NO SEPARATE VERB. The docstring migration is the same Tier-A `frob check --fix`
fix as the comment-run one, not a new command an agent has to remember.

Split because T-4694 was already at three points (Tier-A registration, the ledger
write inside the fix transaction, the archived-path DuplicateId hazard,
idempotency, the judgement-limitation doc). This leaf adds a SECOND DESTINATION
TYPE -- docs/modules file writes with heading creation and a `frob:doc` pointer
emitted onto the symbol -- which is its own 2-3 points. Blocked by T-4694 because
it reuses that leaf's transaction and idempotency machinery rather than inventing
a parallel one.

VOLUME: 1,055 docstrings over 20 lines, 38,964 lines, measured 2026-09-19 over
src/frob/**/*.py (scratchpad/struct.py). This is the largest single instance in
T-2994's whole epic -- roughly four times the comment-run bloat.

THE MECHANICAL RULE (this is deliberately not a judgement call; the judgement
happens in review, see CONDENSATION below):
- KEEP the first paragraph as the docstring. That is the utility summary
  T-2994's doctrine asks for and the tier bar `docs/modules/docstrings.md` sets.
- ROUTE THE REMAINDER by the same rule the comment-run fix already uses:
  - a `T-####` is cited in the docstring  -> append the remainder to that
    ticket's body, exactly as the comment-run path does.
  - no ticket cited                        -> append to
    `docs/modules/<module>.md` under a heading named for the symbol, and leave a
    `frob:doc` pointer on the symbol so the edge is tracked and DRIFT001/COV001
    can see it.
- IDEMPOTENT. Running `--fix` twice must not duplicate prose into either
  destination. Same requirement, same hazard, as T-4694.
- REFUSES when the target ticket does not exist. A dangling `T-####` must abort
  that one fix and report it, never silently drop the prose and never invent the
  ticket. This is T-2994's MOVE-NEVER-DELETE constraint at the mechanical level.

POSITIVE CONTROL: a fixture module with two long docstrings -- one citing a
ticket, one citing none. After `--fix`: the cited one's remainder is in that
ticket's body, the uncited one's remainder is in `docs/modules/<module>.md` under
a heading named for the symbol with a `frob:doc` pointer on the symbol, both
docstrings retain exactly their first paragraph, and a second `--fix` is a no-op.

THE ACCEPTANCE THAT MATTERS MOST -- BYTE-FOR-BYTE IDENTICAL COV/TEST FINDINGS
AFTER. Docstrings are load-bearing for the coverage gates: COV002 keys off a
public symbol having a docstring, and the `frob:doc` edges feed DRIFT001/COV001.
A fix that shortens 1,055 docstrings and shifts the COV/TEST finding set by even
one entry has changed the enforcement surface, not just prose. Diff the finding
sets before and after and require them equal -- a green check on its own proves
nothing here.

CONDENSATION IS A REVIEW STEP, NOT AN AUTHORING STEP (owner's note). The fix
RELOCATES prose mechanically. Agents CONDENSE the relocated prose when they review
the diff -- they do not hand-author the moves. That division is what keeps 38,964
lines tractable: the machine does the 1,055 moves, the humans/agents edit the
result down. The companion size lint on docs/modules exists so the relocated prose
cannot simply pile up unread at the destination.
