## Done report

Confirmed `exclusive` is a genuinely live, current strata parser
keyword before touching the grammar (per the ticket's own explicit
instruction to check this first, since the opposite fix -- the test
being stale -- was equally possible). `strata-core/src/parse/
grammar_node.rs:403` calls `self.at_keyword("exclusive")` for the
T-1627 `may "ATOM" via "GLOB" exclusive` trailer syntax (single
symbol-form via, asserting sole ownership); this is live production
parser code, not dead/removed syntax, and `src/frob/strata/_ast.py`/
`_models.py`/`_elaborate.py`/`_infra.py` all thread an `exclusive`
field through the Python-side AST/model layer that consumes it. So the
GRAMMAR was missing a real keyword -- the code side was correct, per
the ticket's own diagnosis.

Fix: added `exclusive` to `editors/vscode-strata/syntaxes/strata.
tmLanguage.json`'s `clause-keywords` pattern, in alphabetical order
between `errors_total` and `fanout` (matching the existing list's own
ordering convention). Single-keyword addition, no other grammar change
-- did not touch the parser side, per the ticket's explicit scope note
(this test is deliberately one-directional, parser -> grammar only).

### Evidence

tests/unit/test_strata_tmlanguage.py::test_clause_keywords_covered_by_grammar
(designated repro, FAILED_AT_PARENT confirmed against 654a4374cb246383730c3ef92bbf651e752ab730)

### Both-directions controls (measured)

- Positive: full file re-run after the fix -- 12/12 passed
  (`pytest tests/unit/test_strata_tmlanguage.py` exitstatus=0
  collected=12 failed=0).
- Negative (deliberate re-break, confirmed fail, then restored):
  removed `exclusive` from the grammar's clause-keywords pattern again
  -> re-ran `test_clause_keywords_covered_by_grammar` -> FAILED with
  `AssertionError: parser clause keywords missing from tmLanguage
  clause-keywords: ['exclusive']` (exact match to the original failure)
  -> restored the fix, re-ran full file -> 12/12 passed again.

### Gates

`uv run frob ticket evidence T-2636 --check-repro` /
`--designate-repro`: FAILED_AT_PARENT, confirmed (not NO_VERDICT /
PASSED_AT_PARENT). Single-file JSON edit; `frob check --ticket T-2636`
run pre-land per playbook section 0/6g.

### Changed
```
 tickets/T-2636/ticket.md | 8 ++++++--
 1 file changed, 6 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/unit/test_strata_tmlanguage.py::test_clause_keywords_covered_by_grammar` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV001@src/frob/gates/_rule_id_scan.py, COV001@src/frob/strata/_multifile.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_milestone.py, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC006@tickets/T-2570/ticket.md, DOC008@docs/modules/gates.md, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, RENDER001@src/frob/release/_cli.py, SEC004@tests/test_tickets_organization.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
