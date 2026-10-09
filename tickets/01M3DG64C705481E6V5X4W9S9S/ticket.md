+++
id = "01M3DG64C705481E6V5X4W9S9S"
title = "`frob check --fix` TEST010 MOVE handler corrupts Python: re-parse after every Tier-A edit and roll back on failure"
type = "bug"
category = "todo"
priority = "medium"
reporter = "agent"
created = "2026-09-26T00:00:00Z"
updated = "2026-10-09T20:42:37Z"
aliases = ["T-6535"]
labels = ["v1-cluster:C4a", "triage:accepted"]
scope = ["src/frob/gates/_fix_engine_tier_b.py", "src/frob/gates/_fix_engine_text.py", "src/frob/gates/_fix_engine.py", "tests/unit/gates/test_fix_engine_roundtrip.py", "docs/design/rules.md"]
+++

Source: logand.app-v2 FROBLEMS.md (peer coordinator report, 2026-09-26, frob 0.531.1.dev332). Reproduction lives in that repo (read-only for frob agents); the frob-side positive control must be a fixture here.

F-398: a full `frob check --ticket T-0424 --fix` (~403 hunks) left two files unparsable: backend/.../domain/users/state.py (IndentationError at line 149: the TEST010 MOVE handler inserted the relocated frob:doc/frob:tests block for BOTH production symbols that share one test target, deleting `return row`/`return None` in the process) and backend/.../domain/notifications/mailer.py (unmatched ')' -- a directive re-insertion clobbered a multi-line signature). The baseline tree had no PARTIAL-tree warnings; the corruption is fix-introduced. Inferred root cause: `fix_test010_redundant_test_declaration`'s MOVE case resolves destinations by `GraphSnapshot.symbols[target].span` and does not recompute spans after each textual edit in the same file, so the second insertion for a shared target lands on stale offsets.

Deliver:
1. Every Tier-A text fix re-parses the file it touched (tree-sitter for the file's grammar, `ast.parse` for Python) and rolls the file back to its pre-fix bytes when the parse fails or gains a PARTIAL tree; the fix is reported as skipped with the reason, never applied.
2. Multi-edit files: apply edits back-to-front against original spans, or recompute spans after each edit; shared frob:tests targets (one test for N production symbols) insert once.
3. Positive control: a fixture with two production symbols sharing one test target plus a multi-line signature; without the fix the file breaks, with it the file parses and the directives are placed once.
4. docs/modules/gates.md 'TEST010 redundant test declaration Tier-A fix' states the parse-or-rollback guarantee.
Related: <!-- frob:waive DOC006 reason="future-facing: created by this ticket" -->T-draft-741eded5 (DSTACK001 autofix emits unparsable directives) is the same class; share the round-trip guard.


Land-path variant (logand.app-v2, 2026-09-26): the same MOVE handler runs
inside `frob ticket land`'s pre-land Tier-A step across the whole tree, so
its corruption was committed as "wip: pre-land snapshot for T-0442"
(5f32ff6d, 67 files, 4 in scope) and squashed onto logand main under that
ticket; T-0427's land (dce72944, 46 files) did the same and was caught only
by CrossTicketLeakage. `--dry-run` skips Tier-A (T-4179) so a clean dry run
does not show it. Scope restriction and the disable knob are the separate
critical ticket filed the same day (search title "applies Tier-A fixes
across the WHOLE tree"); this ticket still owns the handler fix itself.
