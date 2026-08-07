---
id: T-0985
title: 'frob fmt: repo-wide run still reformats ~218 files (recompaction drift + noqa-suffix
  lines wrongly wrapped)'
state: done
kind: bug
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_fmt_directives.py
- tests/test_gates_fmt_directives.py
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_gates_fmt_directives.py
  reason: 'T-0985: tests covering the noqa-pragma fix live in the module''s existing
    test file; docs/modules/gates.md''s own T-0441 anchor documents canonicalize_text''s
    contract and must be touched to reflect the noqa escape-hatch addition'
  actor: logan
  at: '2026-07-27'
- op: add
  glob: docs/modules/gates.md
  reason: 'T-0985: tests covering the noqa-pragma fix live in the module''s existing
    test file; docs/modules/gates.md''s own T-0441 anchor documents canonicalize_text''s
    contract and must be touched to reflect the noqa escape-hatch addition'
  actor: logan
  at: '2026-07-27'
evidence:
- tests/test_gates_fmt_directives.py::TestNoqaSuffixPragmaT0985::test_over_long_single_line_with_noqa_e501_is_byte_identical
- tests/test_gates_fmt_directives.py::TestNoqaSuffixPragmaT0985::test_over_long_single_line_with_bare_noqa_is_byte_identical
- tests/test_gates_fmt_directives.py::TestNoqaSuffixPragmaT0985::test_over_long_line_without_noqa_still_wraps
- tests/test_gates_fmt_directives.py::TestRepoWideIdempotenceT0985::test_canonicalizing_twice_over_real_repo_files_is_a_no_op
designated_repro_test: null
threat: null
component: null
---
While verifying T-0984's fix (frob fmt off-by-one wrap bug at the 89-col
boundary), ran `uv run frob fmt src/frob` end-to-end in a clean worktree
after the fix. Even with the off-by-one corrected, the run still reformats
~218 files, for two reasons unrelated to the off-by-one itself:

1. Recompaction drift: many already-canonical-looking multi-line `frob:`
   directive comments were hand-wrapped (or wrapped by an older/looser
   version of the tool) using MORE physical lines than the current
   "fewest lines" canonical form requires. Re-running fmt legitimately
   compacts these to fewer lines -- this is intended canonicalizer
   behavior per the module's own docstring, but it means the bulk of the
   repo's `frob:` comments are not currently in the tool's own canonical
   form, so any repo-wide fmt run today produces a large, mostly-cosmetic
   diff.
2. `# noqa: E501` escape-hatch lines: some `frob:tests`/`frob:waive`
   directives are a single physical line deliberately left over the
   88-col limit with a trailing `# noqa: E501` (used where the content is
   one unbreakable token, e.g. a long dotted pytest node id with no space
   to wrap at). `canonicalize_text` treats the trailing noqa comment as
   part of the directive's own logical text and forcibly wraps these
   too, including a mid-word split in some cases, producing an ugly
   diff and defeating the noqa escape hatch's purpose.

Neither is the T-0984 off-by-one boundary bug (that fix is verified
correct and does not by itself cause any of this out-of-scope
reformatting), and fixing them means touching ~218 files repo-wide -- out
of T-0984's scope (src/frob/gates/_fmt_directives.py only, and even then
only the wrap boundary condition). Filed separately so a repo-wide fmt
sweep + `# noqa: E501`-aware skip logic can be planned and reviewed on
its own, rather than smuggled into this bug fix.