---
id: T-3110
title: 'frob refactor verbs have no realistic corpus test: three independent defects
  shipped and were found by one real extraction'
state: done
kind: bug
origin: human
created: '2026-08-27'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/test_refactor_corpus.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: set
  reason: Record the three-defects-in-one-day measurement and the missing corpus/post-apply-import
    check that let all three ship
  actor: logan
  at: '2026-08-27'
  old_length: 0
  new_length: 4237
evidence:
- tests/test_refactor_corpus.py::TestRefactorCorpus::test_split_moves_symbols_across_every_call_site_shape
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: edf1c4f79e902a68604772f5646993e1362ebb11
---
MEASURED 2026-08-27. `frob refactor split` produced THREE distinct, independent
defects in a single day, every one of them found by attempting ONE real
extraction (`frob.gates._models` -> `frob.findings`, four value types out of a
14-symbol module with ~98 importers). Chronologically:

  1. T-3066 -- FALSE REFUSAL. `_shares_line_with_sibling_statement()` used
     `ast.walk`, which yields ancestor compound statements whose line span
     overlaps their own body, so every function-local or block-nested import
     was misclassified as semicolon-joined. ~40 bogus findings; the split
     refused to run at all.
  2. T-3105 -- SILENT CORRUPTION. `_handle_from_import` repointed the WHOLE
     from-import line at the destination even when the line also named
     untouched symbols. Roughly 130 files rewritten wrongly, including
     `gates/__init__.py`'s own re-export line pulling all 14 names from a
     module defining 4. The split reported success=True and left the repo
     unable to import.
  3. T-3109 -- INDENTATION LOSS. `_rebuild_from_import`/`_import_op` writes the
     replacement import with no leading whitespace, so replacing an indented
     import drops its indentation and produces "unexpected indent". Caught by
     the split's own Verify phase, rolled back cleanly.

THE COMMON CAUSE IS NOT THE INDIVIDUAL BUGS. It is that this verb had NEVER
been exercised against a realistic target. Its existing tests use small,
synthetic modules; every one of the three defects requires a call-site shape
that only appears at scale -- a nested import, a mixed moved/unmoved import
line, an indented import. The verb was shipped, tested, documented, and wrong
in three independent ways simultaneously.

Note the severity gradient, which is the actionable part: defect 1 refused
loudly (cheap), defect 3 was caught by the verb's own Verify phase and rolled
back (correct behaviour, working as designed), but defect 2 reported
`success=True` and corrupted 130 files. The Verify phase is the thing that
made two of three survivable. Anything that strengthens it pays for itself.

WHAT IS WANTED: a REALISTIC CORPUS TEST for the refactor verbs -- one that
exercises `split`, `move`, `move-module` and `rename` against a target with the
call-site shapes that actually occur in this repo:
  - a function-local import
  - an `if TYPE_CHECKING:`-guarded import
  - a `try:`/`except ImportError:`-guarded import
  - an INDENTED import at several nesting depths
  - a from-import line naming BOTH moved and unmoved symbols
  - a re-export line naming many symbols (the `__init__.py` shape)
  - a relative import (`from . import X`, `from .mod import Y`)
  - an aliased import (`from m import X as Y`)
  - a symbol referenced in a `.strata` `code=` binding, a ticket `scope` glob,
    and a `frob:doc`/`frob:tests` path citation (the non-Python reference
    surface these verbs are specifically supposed to handle)
Each verb must leave the corpus IMPORTABLE and behaviour-identical afterwards.
"Importable" is the minimum bar defect 2 failed, and it is trivially checkable.

CONSIDER ALSO: an unconditional post-apply import check. Defect 2 shipped
`success=True` on a repo that could not `import frob.gates._models`. A verb
that rewrites imports should not be able to report success without confirming
the tree still imports.

DO NOT let this ticket become a rewrite of the refactor engine. The three
individual defects have their own tickets (two landed, T-3109 outstanding).
This ticket is about the missing test corpus and the missing post-apply
check that let all three ship.

ACCEPTANCE
- A corpus fixture exists covering the shapes listed above, and each refactor
  verb is exercised against it.
- Each of the three known defects is demonstrated to be caught by the corpus:
  check out the pre-fix commit for T-3066, T-3105 and T-3109 in turn (or
  reintroduce the defect) and show the corpus test FAILS. A corpus that does
  not catch the bugs we already know about is not evidence of anything.
- The corpus asserts the result is IMPORTABLE, not merely that the diff looks
  right.
- Report whether any FOURTH defect is found while building it. Given the rate,
  budget for that outcome rather than being surprised by it.