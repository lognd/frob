---
id: T-0994
title: frob fmt wrap-boundary drops the word-join space before a directive's trailing
  attribute, corrupting the rejoined target (e.g. frob:tests ... kind=)
state: dropped
kind: bug
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_fmt_directives.py
- src/frob/graph/dsl.py
- tests/test_gates_fmt_directives.py
- tests/unit/graph/test_dsl.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
Discovered while re-attempting T-0988's repo-wide `frob fmt .` recompaction
after T-0987 landed (the frob:-shaped-continuation-prose misparse fix).
T-0987's fix was necessary but not sufficient: a second, distinct wrap-
boundary bug in `_fmt_directives.py`'s canonicalizer corrupts a directive's
own logical text across the wrap point, rather than merely misplacing a
prose token.

Repro: `tests/test_gates.py`'s original (pre-fmt, HEAD) line is one single
over-limit `frob:tests` directive with a trailing `kind="..."` attribute:

```
    # frob:tests tests/test_gates.py::TestConventionUnitBinding.test_test009_satisfied_by_e2e_edge kind="unit"
```

Running `frob fmt .` wraps this at the word boundary right after
`test_test009_satisfied_by_e2e_edge`, but drops the space that separated
it from ` kind="unit"` when placing the continuation backslash -- the
canonicalizer emits:

```
    # frob:tests \
    # tests/test_gates.py::TestConventionUnitBinding.test_test009_satisfied_by_e2e_edge\
    #  kind="unit"
```

Note there is NO space before the second line's trailing `\`. When
`frob.graph.dsl.parse_directives` rejoins continuation lines it (correctly,
per T-0987's fix) folds them back into one logical string, but folding
drops the newline with no space substituted at a no-space-before-backslash
join point -- concatenating `..._e2e_edge` directly onto `kind="unit"`
with nothing between them, producing the corrupted target string
`test_test009_satisfied_by_e2e_edgekind="unit"`. This breaks the `frob:tests`
edge itself: `frob check --only affect_drift` reports a NEW DRIFT002 ("tests
edge ... no longer resolves; candidates: no candidates found") that does not
exist on HEAD before the recompaction.

This is a different bug class from T-0987 (which fixed a prose token being
MISPARSED as a bogus new directive; the text itself round-tripped correctly
once parsed). Here the directive parses as A single directive fine, but its
TARGET text is silently corrupted -- a wrap point split a token run without
preserving the word-boundary space, and rejoining does not restore it.
Likely root cause: the wrap-boundary chooser in `_fmt_directives.py` treats
the trailing `kind="..."` attribute as freely re-wrappable prose (like a
`reason="..."` value) and wraps right at the space before it, but then
either (a) does not preserve that boundary space when emitting the
continuation backslash, or (b) the DSL's own line-rejoin logic in
`frob.graph.dsl` (post-T-0987) drops it. Needs a read of both
`_fmt_directives.py`'s wrap-emission and `parse_directives`'s rejoin path
to confirm which side owns the fix -- not yet root-caused past this repro.

Filed instead of forcing T-0988's recompaction through a second time: this
is exactly the disposition T-0985/T-0987 already established (do NOT run
the repo-wide sweep while it is provably still corrupting live directive
references). T-0988 remains blocked on this new ticket.

## Repro steps
1. On a clean checkout at this repo's HEAD, run `frob fmt tests/test_gates.py`.
2. Inspect `tests/test_gates.py` around `test_test009_satisfied_by_e2e_edge`:
   the continuation line ends in `_e2e_edge\` with no space before the
   backslash, while the next line starts with `  kind="unit"` (a leading
   space that the rejoin does not compensate for).
3. Run `frob check --only affect_drift` on the result: a DRIFT002 fires
   for `TestConventionUnitBinding.test_test009_satisfied_by_e2e_edge`
   ("no longer resolves; candidates: no candidates found") that is absent
   on unmodified HEAD.

## Plan
1. Read `_fmt_directives.py`'s wrap-emission logic around how it decides
   whether a continuation backslash is preceded by a join-space vs a
   mid-word split, and `frob.graph.dsl.parse_directives`'s rejoin logic
   (both touched by T-0987) to find which side drops the space.
2. Fix so a wrap at a real word boundary (a boundary that had a space in
   the original single-line text) round-trips through wrap-then-rejoin
   byte-for-word-identical -- add a regression test pinning exactly this
   repro shape (a `frob:tests <target> kind="..."` directive whose target
   is long enough to force a wrap right before `kind=`).
3. Re-verify the same script T-0985/T-0987/T-0988 used (whitespace-
   collapsed hunk-pair token equality) additionally checks that NO join
   point silently drops or duplicates a token boundary -- not just that
   comment markers/backslashes fold away cleanly.
4. Once fixed, T-0988 can retry the repo-wide recompaction.

## Acceptance
- A `frob:tests <target> kind="..."` (or any directive) whose only
  attribute is pushed past the wrap column round-trips through
  `frob fmt` with its target string byte-identical after DSL rejoin.
- `frob check --only affect_drift` reports 0 new DRIFT002/AFFECT001
  findings from a fresh repo-wide `frob fmt .` relative to pre-fmt HEAD.
- Regression test added pinning the exact `test_test009_satisfied_by_e2e_edge`
  repro shape.

## Drop reason
- 2026-07-27: absorbed by T-0991 (landed 498ff58a), same bug: fmt wrap dropping the word-boundary space before a directive's trailing attribute