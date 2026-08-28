## Done report

Changed:
- src/frob/app/ticket_runner/_land_cmd.py::_public_top_level_defs (decorator-
  aware directive-search line: uses `node.decorator_list[0].lineno` when a
  top-level def/class is decorated, instead of `node.lineno` which `ast`
  always sets to the `def`/`class` keyword's own line)
- tests/test_ticket_work_and_land_finish.py::TestAssertNewPublicSymbolsHaveDocAndTestEdges.test_a_decorated_new_class_with_directives_above_decorator_not_refused
  (must-now-fire control)
- tests/test_ticket_work_and_land_finish.py::TestAssertNewPublicSymbolsHaveDocAndTestEdges.test_a_decorated_new_symbol_with_no_edges_still_refuses_positive_control
  (must-still-pass control)

Method (per this ticket's requirements):
- TOKEN/GRAMMAR-based, never lexical: the fix reads `ast.FunctionDef/
  AsyncFunctionDef/ClassDef.decorator_list[0].lineno` from the SAME
  `ast.parse` tree `_public_top_level_defs` already builds -- no
  substring/regex added. This mirrors `frob.lang._walk_python._effective_
  node`'s existing tree-sitter `decorated_definition` peeling for the
  identical directive-to-symbol binding question, ported to this module's
  separate ast-based text scan (as the ticket's own Suggested direction
  specified) rather than sharing frob.lang's tree-sitter substrate.
- Repro measured directly, not assumed: reproduced the exact symptom with
  a synthetic file (`@dataclass(frozen=True)\nclass BrandNewDecoratedClass`
  with `frob:doc`/`frob:tests` directly above the decorator, the identical
  shape T-2585's `GateRunReplay` hit and had to work around). Verified by
  temporarily reverting only `_land_cmd.py` to its pre-fix content in the
  worktree (`git checkout --`) with the new test committed alone first
  (commit 78054e5a2) -- the test genuinely FAILS at that parent (refused
  the land with "no frob:doc, frob:tests edge"), confirmed via
  `frob ticket evidence --designate-repro` returning FAILED_AT_PARENT (a
  real repro, not forced/confirmatory-only). Restoring the fix makes it
  pass.
- Must-still-pass control: a second synthetic file, decorated with
  genuinely NO directives anywhere (not even above the decorator), still
  refuses the land with SystemExit(1) -- the decorator-lineno offset only
  moves WHERE the directive-block search starts, it does not create a new
  exemption for decorated symbols in general.
- Whole-class regression check: `pytest tests/test_ticket_work_and_land_
  finish.py::TestAssertNewPublicSymbolsHaveDocAndTestEdges` -- 8 of 9
  tests pass (the 2 new ones plus all 6 pre-existing ones in the class,
  unchanged); the 1 remaining failure
  (test_cli_land_end_to_end_refuses_a_worktree_with_a_new_undocumented_symbol)
  is a PRE-EXISTING failure unrelated to this diff -- verified by
  reverting the fix entirely (`git apply -R` on the isolated diff) and
  confirming it fails identically with or without this ticket's change
  (an unrelated TICK013 empty-scope refusal the fixture's own `new_ticket`
  call trips over, outside this ticket's scope).
- `frob check --ticket T-2609`: gate:AFFECT/gate:SCOPE/gate:PRE clean
  (the only three families this check narrows to the ticket's touched
  set); every other FAIL in that run (ruff-format, frob-cycle, gate:COV/
  DOC/TICK/WIRE, claude-config-drift) is pre-existing repo-wide baseline
  noise, none of it in a file this ticket touched.

Evidence: tests/test_ticket_work_and_land_finish.py::TestAssertNewPublicSymbolsHaveDocAndTestEdges::test_a_decorated_new_class_with_directives_above_decorator_not_refused
(designated repro, genuine FAILED_AT_PARENT verdict against commit
78054e5a2 -- the test-only commit preceding the fix commit),
tests/test_ticket_work_and_land_finish.py::TestAssertNewPublicSymbolsHaveDocAndTestEdges::test_a_decorated_new_symbol_with_no_edges_still_refuses_positive_control

Filed: none.

Gates: `frob check --ticket T-2609` clean on gate:AFFECT/gate:SCOPE/
gate:PRE; other FAILs are pre-existing repo-wide baseline, confirmed
unrelated by direct revert-and-compare.

### Changed
```
 src/frob/app/ticket_runner/_land_cmd.py   | 33 +++++++++++----
 tests/test_ticket_work_and_land_finish.py | 68 +++++++++++++++++++++++++++++++
 tickets/T-2609/ticket.md                  | 35 +++++++++++++++-
 3 files changed, 127 insertions(+), 9 deletions(-)
```

### Evidence
- `tests/test_ticket_work_and_land_finish.py::TestAssertNewPublicSymbolsHaveDocAndTestEdges::test_a_decorated_new_class_with_directives_above_decorator_not_refused` (pytest node id, verified passing when recorded)
- `tests/test_ticket_work_and_land_finish.py::TestAssertNewPublicSymbolsHaveDocAndTestEdges::test_a_decorated_new_symbol_with_no_edges_still_refuses_positive_control` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 18 error(s), 584 warning(s), 846 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV004@tickets/T-2195/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-2244/attachments/01-t-2244-audit-safe-to-repoint-split-test-typecheck-safe-now-lint-blocked-by-newly-found-t-2387-not-t-2359-format-lint-fix-blocked-by-both-test-fast-stays-raw.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, COV004@tickets/T-2328/attachments/02-third-reproduction-t-2323-confirmed-workaround-pre-commit-the-file-yourself-before-land.md, COV004@tickets/T-2328/attachments/03-clarification-titled-work-loss-defect-remains-open-carried-by-t-2351.txt, COV004@tickets/T-2350/attachments/01-diagnosis-timing-visibility-race-not-identity-matching-both-candidate-fix-files-leased-by-t-2351-no-edit-attempted.md, COV004@tickets/T-2543/attachments/01-class-a-options-and-measured-costs-t-2377-survey.md, CYCLE001@src/frob/__init__.py, DOC006@docs/guides/coordinator-scripts.md, DOC006@docs/modules/gates.md, DOC006@tickets/T-2886/ticket.md, DOC008@docs/commands/check.md, TICK004@tickets.md, WIRE002@src/frob/tickets/_unlanded.py
