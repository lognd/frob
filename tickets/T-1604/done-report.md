## Done report

Adds Bash/Shell as a registered `frob.lang` language, mirroring kotlin's
adapter shape (`_walk_kotlin.py`/T-0613+T-0723) end to end.

Changed:
src/frob/lang/_walk_bash.py (new)
src/frob/lang/_extract.py::COMMENT_TYPES
src/frob/lang/_extract.py::_WALKERS
src/frob/lang/_extract.py::_imports_bash
src/frob/lang/_extract.py::_IMPORT_WALKERS
src/frob/lang/__init__.py::_EXTENSION_TABLE
src/frob/lang/_support.py::_capability_call_graph_status
src/frob/gates/_lang_conformance.py::_CAPABILITY_FIXTURE_SOURCES
src/frob/gates/_lang_conformance.py::_CAPABILITY_FIXTURE_EXTENSIONS
frob.toml ([[test.runner]] language="bash")
tests/fixtures/lang/sample.sh (new)
tests/test_lang.py::TestBash (new)
tests/test_lang_conformance_gate.py::TestBashCapabilityConformance (new)
docs/modules/lang.md (publicness table, per-language walker notes)

Publicness decision (required by the ticket, documented in
`_walk_bash.py`'s own module docstring): bash has no visibility keyword
at all, so `_bash_public` adopts the leading-underscore convention
(shellcheck's own idiom), same shape as python's rule. Symbol shape:
only top-level `function_definition` and top-level `variable_assignment`
(bare or `export`/`readonly`/`declare`/`local`-wrapped) become symbols;
nested assignments and bare top-level statements (loops, ifs, bare
commands) are deliberately not symbol-shaped, disclosed in the module
docstring per the ticket's own framing.

Directive DSL: bash's one comment form (`# ...`, no block comments)
reuses `frob.lang._extract`'s language-agnostic block-comment chaining
for continuation folding -- no bash-specific continuation logic needed.
Verified with a real `# frob:tests \` / `# <target>` continuation fixture
and a MUST-FAIL broken-continuation positive control.

Obligation-graph participation: doc edges (docs/modules/lang.md),
test edges (frob:tests on every new public/private symbol), waivers
(frob:waive WIRE001 on `_parse_bash`, a deliberately test-only helper
mirroring kotlin's `parse_kotlin` before its own dispatch wiring
landed) all behave as they do for python/kotlin -- verified via
`frob check --ticket T-1604 --no-cache`.

Capability conformance (T-1599's 6-of-7 axis): symbol_walk, publicness,
doc_extract, directive_parse, import_graph are IMPLEMENTED and
behaviorally verified (LANG004/TestBashCapabilityConformance).
call_graph is a reasoned KNOWN_GAP: bash invokes a function via bare-word
syntax (`foo`, never `foo()`), which frob.graph.callgraph's shared
token-adjacency call detector cannot recognize -- a genuine shared-layer
gap, filed separately per the ticket's own "special case is evidence the
abstraction is wrong" instruction, not special-cased into the shared
detector. test_discovery stays structural-only (same disclosed posture
as typescript/c/cpp/kotlin -- no bounded, offline-safe bash test-runner
toolchain integration exists yet).

Positive/negative controls:
- Positive (must-pass): tests/fixtures/lang/sample.sh -- a public
  function, a private (`_hidden`) function, an exported top-level
  constant, a leading doc comment, all extracted correctly
  (tests/test_lang.py::TestBash).
- Positive (must-fail #1): TestBashCapabilityConformance::
  test_bash_broken_continuation_fixture_is_caught_not_rubber_stamped --
  a fixture whose `frob:tests \` continuation's second line is dropped
  must fail directive_parse's behavioral check.
- Positive (must-fail #2): TestBashCapabilityConformance::
  test_bash_no_symbols_fixture_is_caught_not_rubber_stamped -- an
  empty bash fixture must fail symbol_walk's behavioral check.

Evidence: 10 node ids bound via `frob ticket evidence T-1604` (see
ticket.md), all passing via `uv run frob test` (touched-set) and
`uv run pytest -q tests/test_lang.py::TestBash
tests/test_lang_conformance_gate.py::TestBashCapabilityConformance`.

Filed: T-2901 (renumbers at land) -- shared-layer finding
against `frob.graph.callgraph`'s call-detection heuristic (bare-word
bash invocation unrecognized), scope `src/frob/graph/callgraph.py`.

Gates: `frob check --ticket T-1604 --no-cache` clean for every gate this
ticket's own scope touches (LANG, WIRE, SCOPE, PRE, ruff-check). Every
remaining FAIL in the full run (gate:COV/DOC/TICK, frob-cycle,
ruff-format, claude-config-drift) is pre-existing and unrelated to this
diff -- confirmed by grepping each failing gate's file list for
`_walk_bash`/`bash`/`lang_conformance` and finding no hits.

### Changed
```
 tickets/T-1604/ticket.md           | 70 +++++++++++++++++++++++++++++++++++++-
 tickets/T-2901/ticket.md | 53 +++++++++++++++++++++++++++++
 2 files changed, 122 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_lang.py::TestBash::test_walks_top_level_function` (pytest node id, verified passing when recorded)
- `tests/test_lang.py::TestBash::test_private_symbol_is_not_public` (pytest node id, verified passing when recorded)
- `tests/test_lang.py::TestBash::test_top_level_variable_assignment` (pytest node id, verified passing when recorded)
- `tests/test_lang.py::TestBash::test_leading_comment_binds_as_doc_text` (pytest node id, verified passing when recorded)
- `tests/test_lang.py::TestBash::test_nested_assignment_is_not_a_symbol` (pytest node id, verified passing when recorded)
- `tests/test_lang.py::TestBash::test_bash_no_block_comment_form` (pytest node id, verified passing when recorded)
- `tests/test_lang.py::TestBash::test_parse_bash_produces_a_tree` (pytest node id, verified passing when recorded)
- `tests/test_lang_conformance_gate.py::TestBashCapabilityConformance::test_bash_registered_capabilities_pass` (pytest node id, verified passing when recorded)
- `tests/test_lang_conformance_gate.py::TestBashCapabilityConformance::test_bash_broken_continuation_fixture_is_caught_not_rubber_stamped` (pytest node id, verified passing when recorded)
- `tests/test_lang_conformance_gate.py::TestBashCapabilityConformance::test_bash_no_symbols_fixture_is_caught_not_rubber_stamped` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 10 passed (from 10 evidence id(s))
- gates: 18 error(s), 542 warning(s), 846 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV004@tickets/T-2195/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-2244/attachments/01-t-2244-audit-safe-to-repoint-split-test-typecheck-safe-now-lint-blocked-by-newly-found-t-2387-not-t-2359-format-lint-fix-blocked-by-both-test-fast-stays-raw.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, COV004@tickets/T-2328/attachments/02-third-reproduction-t-2323-confirmed-workaround-pre-commit-the-file-yourself-before-land.md, COV004@tickets/T-2328/attachments/03-clarification-titled-work-loss-defect-remains-open-carried-by-t-2351.txt, COV004@tickets/T-2350/attachments/01-diagnosis-timing-visibility-race-not-identity-matching-both-candidate-fix-files-leased-by-t-2351-no-edit-attempted.md, COV004@tickets/T-2543/attachments/01-class-a-options-and-measured-costs-t-2377-survey.md, CYCLE001@src/frob/__init__.py, DOC006@docs/guides/coordinator-scripts.md, DOC006@tickets/T-2880/ticket.md, DOC006@tickets/T-2884/ticket.md, DOC006@tickets/T-2886/ticket.md, TICK004@tickets.md, TICK006@tickets.md
