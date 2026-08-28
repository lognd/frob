## Done report

Wire-or-drop verdict: DROP (delete). `_parse_csharp` (src/frob/lang/_walk_csharp.py) was a raw tree-sitter parse helper wrapping `get_parser(_GRAMMAR_NAME)` with no production caller -- `frob.lang.__init__`'s `_parse` dispatch loads every grammar through its own generic `get_parser(grammar_name)` chokepoint, never through this module. No future consumer materialized (the ticket's own stated condition for dropping, same shape as its bash sibling T-2900). Deleted `_parse_csharp` and its now-orphaned `_GRAMMAR_NAME` constant and `Tree`/`get_parser` imports; inlined `get_parser("csharp")` directly in the one test that exercised it (tests/test_lang.py::TestCSharp.test_parse_csharp_produces_a_tree).

Detector measurement (deletion-as-detector-test, done BEFORE deleting): temporarily removed the `frob:waive WIRE001 follow_up="T-2905"` comment and ran `frob check --json --only gates --ticket T-2905` against the known-dead symbol.

Miss set (identical to T-2900's bash measurement):
- WIRE001: MISS -- did not fire at all once the waiver was removed, despite the ticket being filed as "WIRE001's required follow-up ticket".
- REF002: MISS -- did not fire either.
- DEAD001: HIT -- correctly fired as a WARN: "DEAD001: src/frob/lang/_walk_csharp.py::_parse_csharp is a private symbol with no call-graph caller and no frob:tests/frob:describes/frob:invariant edge -- wire it, delete it, or frob:waive DEAD001 reason=...".

Same result as T-2900: of the three named detectors, only DEAD001 caught the known-dead symbol. Waiver was restored (working tree confirmed byte-identical to before the experiment) before proceeding to the real deletion.

Changed:
- src/frob/lang/_walk_csharp.py: deleted `_parse_csharp`, `_GRAMMAR_NAME`, and the now-unused `Tree`/`get_parser` imports.
- tests/test_lang.py::TestCSharp.test_parse_csharp_produces_a_tree: rewritten to call `tree_sitter_language_pack.get_parser("csharp")` directly instead of the deleted wrapper; same assertions, same coverage.

Evidence: tests/test_lang.py::TestCSharp::test_parse_csharp_produces_a_tree (rewritten); full tests/test_lang.py run = 85 passed, 0 failed.

Filed: none.

Gates: `frob check --json --ticket T-2905` (unbudgeted, gate-summary present) -- 0 errors touching src/frob/lang/_walk_csharp.py or tests/test_lang.py.

### Changed
```
 tickets/T-2905/ticket.md | 12 +++++++++++-
 1 file changed, 11 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_lang.py::TestCSharp::test_parse_csharp_produces_a_tree` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 21 error(s), 521 warning(s), 847 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV004@tickets/T-2195/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-2244/attachments/01-t-2244-audit-safe-to-repoint-split-test-typecheck-safe-now-lint-blocked-by-newly-found-t-2387-not-t-2359-format-lint-fix-blocked-by-both-test-fast-stays-raw.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, COV004@tickets/T-2328/attachments/02-third-reproduction-t-2323-confirmed-workaround-pre-commit-the-file-yourself-before-land.md, COV004@tickets/T-2328/attachments/03-clarification-titled-work-loss-defect-remains-open-carried-by-t-2351.txt, COV004@tickets/T-2350/attachments/01-diagnosis-timing-visibility-race-not-identity-matching-both-candidate-fix-files-leased-by-t-2351-no-edit-attempted.md, COV004@tickets/T-2543/attachments/01-class-a-options-and-measured-costs-t-2377-survey.md, CYCLE001@src/frob/__init__.py, DOC006@docs/guides/coordinator-scripts.md, DOC006@docs/modules/gates.md, DOC006@tickets/T-2886/ticket.md, DOC006@tickets/T-2920/ticket.md, DOC006@tickets/T-2923/ticket.md, DOC008@docs/commands/check.md, PRE001@tickets/T-2905, TICK004@tickets.md, WIRE002@src/frob/tickets/_unlanded.py
