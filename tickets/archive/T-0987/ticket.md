---
id: T-0987
title: frob.graph.dsl misparses a directive continuation line whose prose starts with
  a frob:-shaped token
state: done
kind: bug
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/graph/dsl.py
- tests/unit/graph/test_dsl.py
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/graph/test_dsl.py
  reason: T-0987 regression coverage + doc-drift fix for AFFECT001
  actor: logan
  at: '2026-07-27'
- op: add
  glob: docs/modules/gates.md
  reason: T-0987 regression coverage + doc-drift fix for AFFECT001
  actor: logan
  at: '2026-07-27'
evidence:
- tests/unit/graph/test_dsl.py::TestVerbShapedContinuationProse::test_frob_describes_prose_at_continuation_line_start_folds
- tests/unit/graph/test_dsl.py::TestVerbShapedContinuationProse::test_frob_describes_prose_repro_shape_from_dup_core
- tests/unit/graph/test_dsl.py::TestVerbShapedContinuationProse::test_property_wrap_at_every_width_preserves_reason
- tests/unit/graph/test_dsl.py::TestVerbShapedContinuationProse::test_stacked_directives_still_parse_independently
- tests/unit/graph/test_dsl.py::TestVerbShapedContinuationProse::test_unrelated_directives_corruption_repro_still_rejects_fold
designated_repro_test: null
threat: null
component: null
---
## Description

Discovered while verifying T-0985 (frob fmt: repo-wide run still reformats
~218 files). T-0985 fixed the `# noqa: E501` escape-hatch half of that
ticket, but the other half -- doing the one-time repo-wide recompaction so
`frob fmt` becomes idempotent-at-zero -- turned out to be UNSAFE to do
blindly, because it exposes a real, separate bug in
`frob.graph.dsl.parse_directives` (or its comment-run folding path):

A directive's `reason="..."` prose can legitimately contain the literal
substring `frob:describes` (or any other `frob:VERB`-shaped token) as
prose, not as an actual directive -- e.g. `src/frob/vet/_allow.py`:

```
# frob:waive COV007 reason="docs/modules/vet.md's Public API section \
# individually frob:describes this private helper by name (T-0529) -- a \
# deliberate architecture doc, not accidental drift onto a private helper"
```

This round-trips fine through `canonicalize_text`'s minimal-line
recompaction (T-0441's own contract: same logical text, just re-wrapped),
but if the NEW wrap boundary happens to land such that `frob:describes`
becomes the first token on its OWN physical line (after the `# `
marker is stripped), `parse_directives` misidentifies that continuation
line as the START of a brand-new directive -- `frob:describes` is not a
real verb, so it reports `MalformedDirective`s: `bad attribute syntax`
on the previous line and `unknown verb 'describes'` on this one.

Verified directly: parsing the ORIGINAL (HEAD) `src/frob/vet/_allow.py`
and `src/frob/dup/_core.py` through `frob.lang.parse_file` +
`frob.graph.dsl.parse_directives` produces 0 malformed directives; parsing
the SAME files after T-0985's repo-wide recompaction (pure rewrap, no
logical-text change) produces 2 and 12 malformed directives respectively,
purely from the wrap-boundary shift. Running T-0985's recompaction
repo-wide amplified this to 90 DSL errors and cascaded into dozens of new
test failures repo-wide (`tests/test_registry_reconciliation_*.py`
exhaustiveness gates, `tests/unit/test_extending_guides_complete.py` doc
anchors, several `tests/test_ticket_land.py`/`tests/system/
test_cli_ticket*.py` cases) when attempted end-to-end -- see T-0985's
Done report for the exact repro.

## Root cause (best-effort diagnosis, not yet confirmed by reading every
line of `dsl.py`)

The directive scanner in `frob.graph.dsl` appears to classify a physical
comment line as a directive attempt (`frob:VERB ...`) whenever its
content (after marker-stripping) starts with `frob:`, WITHOUT first
checking whether the immediately preceding physical line ended in a
continuation backslash (T-0286's continuation syntax) -- i.e. it does not
consistently fold a continuation run before deciding whether a physical
line looks like a directive start. A genuine directive's continuation
lines are free-form prose and must never be independently re-parsed as a
directive, regardless of what token happens to open them.

## Plan (not yet executed -- filed for someone else / a future pass to
pick up)

1. Reproduce minimally: a `# frob:waive R reason="... \` / `# frob:foo
   bar"` two-line directive where the SECOND line's stripped content
   starts with a `frob:`-shaped token that is not itself a directive
   verb.
2. Read `frob.graph.dsl`'s directive-scanning loop (the code path
   `parse_directives` reaches before `fold_comment_runs` is applied, or
   the ordering between the two) to find exactly where a continuation
   line is treated as directive-start-eligible.
3. Fix so continuation lines (previous physical line ending in the T-0286
   backslash, within an already-recognized directive run) are NEVER
   independently scanned for `frob:VERB` -- only genuine run-starts are.
4. Add a regression test: a directive `reason=` whose prose contains a
   `frob:`-shaped substring that lands at the start of a continuation
   line must parse with zero malformed directives.
5. Once (3) is proven safe, T-0985's repo-wide recompaction (deferred by
   this filing) can be reattempted without the cascade of new DSL/test
   failures documented above.

## Acceptance

- Regression test per step 4 passes.
- Re-running T-0985's repro (`src/frob/vet/_allow.py`,
  `src/frob/dup/_core.py` recompacted via `canonicalize_text`) produces
  zero new `MalformedDirective`s.