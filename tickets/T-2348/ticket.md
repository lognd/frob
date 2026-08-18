---
id: T-2348
title: WIRE001 case 3 (_wire001_cli_dest_violations) decides wiring via raw text-membership
  search, not a parsed structure
state: queued
kind: bug
origin: human
created: '2026-08-17'
priority: medium
parent: T-1662
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_wire.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: tests/**
  reason: too broad, collided with T-1604; narrow to a specific test file once implementation
    starts
  actor: logan
  at: '2026-08-17'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while building T-2344 (T-1662's meta-check): `_wire001_cli_dest_
violations` (src/frob/gates/_wire.py) decides WIRE001 case 3 ("a new CLI
`dest=` never reaches `_config_external.py`") via a substring-membership
search over `_config_external.py`'s raw CURRENT text, by the function's
own docstring's admission: "A targeted string-membership check ... is
deliberately used instead of trying to locate the exact copy-loop tuple."

This is wrong in both directions, same shape as every other (c) finding
this epic has fixed:
- FALSE NEGATIVE: a `dest` string that appears anywhere else in
  `_config_external.py` (a comment, an unrelated field with a colliding
  name, a string in a docstring) reads as "wired" even if the real
  copy-loop tuple this new CLI arg needs was never touched.
- FALSE POSITIVE: a `dest` string genuinely wired via a DIFFERENT,
  non-literal mechanism this text search cannot see (e.g. a name built
  from a shared constant/dict rather than typed inline) never matches,
  even though it IS wired.

The docstring's own justification is a real design tradeoff, not a
mistake -- `_build_external_config_kwargs`'s six copy-loop tuples are an
implementation detail this gate should not have to track structurally --
but T-1662's standing principle is that a lexical decision needs an
explicit, reasoned exemption (this epic's own class-(b) table), not a
silent accepted-risk docstring. Two directions to resolve, either is
acceptable:
1. Raise it to semantics: AST-parse `_config_external.py`'s copy-loop
   tuples for real (six tuples, per the docstring) and check dest
   membership against the PARSED set, not raw text -- turns the false-
   negative gap into a real answer.
2. Formally classify it class (b) (accept the docstring's own tradeoff
   as final) and add it to `_lexical_selfcheck._ALLOWLIST`
   (T-2344) with that stated reason, closing this ticket as "reviewed,
   accepted."

Do not silently allowlist this without doing one of the two -- that is
exactly the "catalogued is not enforced" failure this drive keeps paying
for.

Positive control for whichever direction: a deliberately introduced CLI
`dest=` argument wired ONLY through the tuple structure (not a bare
string literal anywhere else in `_config_external.py`) must still be
detected as wired if choice 1 is taken; a `dest=` argument NOT wired at
all must still fire WIRE001 either way.
