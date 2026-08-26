## Done report

Adds C# as a registered `frob.lang` language, mirroring typescript's
field-based adapter shape end to end (tree-sitter-c-sharp exposes real
named fields -- name/body/type/returns/parameters -- unlike kotlin's
almost-field-free grammar, so this walker follows `_walk_typescript.py`'s
recursive-descent-over-`child_by_field_name` shape rather than kotlin's
positional one).

Changed:
src/frob/lang/_walk_csharp.py (new)
src/frob/lang/_extract.py::COMMENT_TYPES / _WALKERS / _imports_csharp / _IMPORT_WALKERS
src/frob/lang/__init__.py::_EXTENSION_TABLE
src/frob/gates/_lang_conformance.py::_CAPABILITY_FIXTURE_SOURCES / _CAPABILITY_FIXTURE_EXTENSIONS / _UNREGISTERED_CANDIDATE_LANGUAGES
src/frob/lang/_support.py (new bash+csharp FACETS-wiring citation, see below)
frob.toml ([[test.runner]] language="csharp")
tests/fixtures/lang/sample.cs (new)
tests/test_lang.py::TestCSharp (new)
tests/test_lang_conformance_gate.py::TestCSharpCapabilityConformance (new)
docs/modules/lang.md (publicness table, per-language walker notes)

Publicness decision (required by the ticket): the literal `public`
keyword only -- both silent defaults (top-level `internal`, member
`private`) are NOT public, matching kotlin's "enumerate the non-public
set" shape rather than rust's "enumerate the public set" shape, since
C#'s silent defaults are exactly as non-public as its explicit keywords.
One carve-out: an interface member with no modifier of its own is
implicitly public (the language's own rule), overridden only by an
explicit non-public modifier -- verified with a real
`test_interface_member_is_implicitly_public` control.

Properties-vs-fields decision (required by the ticket): a
`property_declaration` is C#'s real API-surface member shape, mapped
onto `SymbolKind.CONST` (no first-class "property" kind exists). A
plain field is not symbol-shaped at all (idiomatic-C# implementation
detail); a `const`-modified field IS extracted as `CONST`, mirroring
every other grammar's own const rule. Verified with
`test_property_is_a_const_symbol` / `test_const_field_is_extracted_plain_field_is_not`.

Nullable reference types: verified interactively that `string?`
annotations live inside a declaration's TYPE subtree, never inside its
`name` field, so they cannot confuse name/symbol extraction (no
dedicated test needed -- every existing test already exercises `name`-
field-only lookups; the walker never inspects a type subtree for a name
at all).

Partial classes: disclosed in the module docstring as a real limitation
(each partial fragment walked independently, no cross-fragment symbol
merge) -- frob.lang has no multi-fragment identity concept for any
grammar today, not something this ticket's own scope could fix.

Directive DSL / obligation graph: identical posture to T-1604's bash
adapter -- doc edges, test edges (frob:tests on every new symbol),
waivers (frob:waive WIRE001 on `_parse_csharp`, same test-only-helper
shape as bash's `_parse_bash`) all verified via
`frob check --ticket T-1600 --no-cache`.

Capability conformance (T-1599's 6-of-7 axis): symbol_walk, publicness,
doc_extract, directive_parse, call_graph, import_graph are ALL
IMPLEMENTED and behaviorally verified -- unlike bash, C# calls ARE
parenthesized (`Foo()`), so no call_graph KNOWN_GAP is needed here.
test_discovery stays structural-only (no bounded, offline-safe C# test-
runner toolchain integration exists yet, same disclosed posture as
typescript/c/cpp/kotlin).

Positive/negative controls:
- Positive (must-pass): tests/fixtures/lang/sample.cs -- public class,
  private method, public property, const field, plain (non-extracted)
  field, internal interface with an implicitly-public member, public
  enum, namespace nesting, leading XML doc comment.
- Positive (must-fail #1): test_csharp_broken_continuation_fixture_is_caught_not_rubber_stamped
  -- dropped continuation line must fail directive_parse.
- Positive (must-fail #2): test_csharp_no_symbols_fixture_is_caught_not_rubber_stamped
  -- empty fixture must fail symbol_walk.

Post-land regression found and fixed (not part of T-1600's own scope,
but discovered while building it and fixed here since the file was
already open): once bash's fixture files were actually committed and
tracked (T-1604 land), LANG003 started firing "unsound coverage" for
bash's capability/dup/docblock FACETS -- the auto-generated KNOWN_GAP
detail in those three `_support.py` status functions never cited a
tracking ticket the way `_arch_status` already does for T-0329. Filed
T-2906 (renumbers at land) and added a shared
`_NEW_ADAPTER_LANGUAGES_PENDING_FACET_WIRING` citation covering both
bash and csharp, so csharp's own fixture landing does not repeat the
same regression.

Evidence: 14 node ids bound via `frob ticket evidence T-1600`, all
passing via `uv run frob test` (touched-set) and
`uv run pytest -q tests/test_lang.py::TestCSharp
tests/test_lang_conformance_gate.py::TestCSharpCapabilityConformance`.

Filed:
- T-2905 (renumbers at land) -- wire-or-drop follow-up for
  `_parse_csharp` (WIRE001's required accountable ticket), mirroring
  T-2900 (bash's own identical `_parse_bash` follow-up).
- T-2906 (renumbers at land) -- bash+csharp FACETS-wiring
  finding (capability/dup/docblock subsystem integration), described
  above.

Gates: `frob check --ticket T-1600 --no-cache` clean for every gate
this ticket's own scope touches (LANG, WIRE, SCOPE, DUP, ruff-check).
Every remaining FAIL in the full run (gate:COV/DOC/TICK, frob-cycle,
ruff-format's 15 unrelated files, claude-config-drift) is pre-existing
and unrelated -- confirmed by grepping each failing gate's file list
for `_walk_csharp`/`csharp`/`lang_conformance` and finding no hits.

### Changed
```
 tickets/T-1600/ticket.md           | 75 +++++++++++++++++++++++++++++++++++++-
 tickets/T-2905/ticket.md | 43 ++++++++++++++++++++++
 tickets/T-2906/ticket.md | 52 ++++++++++++++++++++++++++
 3 files changed, 169 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_lang.py::TestCSharp::test_parse_csharp_produces_a_tree` (pytest node id, verified passing when recorded)
- `tests/test_lang.py::TestCSharp::test_walks_class_and_method` (pytest node id, verified passing when recorded)
- `tests/test_lang.py::TestCSharp::test_private_method_is_not_public` (pytest node id, verified passing when recorded)
- `tests/test_lang.py::TestCSharp::test_property_is_a_const_symbol` (pytest node id, verified passing when recorded)
- `tests/test_lang.py::TestCSharp::test_const_field_is_extracted_plain_field_is_not` (pytest node id, verified passing when recorded)
- `tests/test_lang.py::TestCSharp::test_enum_is_a_type_symbol` (pytest node id, verified passing when recorded)
- `tests/test_lang.py::TestCSharp::test_namespace_is_a_transparent_qualname_container` (pytest node id, verified passing when recorded)
- `tests/test_lang.py::TestCSharp::test_interface_member_is_implicitly_public` (pytest node id, verified passing when recorded)
- `tests/test_lang.py::TestCSharp::test_file_scoped_namespace_is_a_transparent_qualname_container` (pytest node id, verified passing when recorded)
- `tests/test_lang.py::TestCSharp::test_leading_xml_doc_comment_binds_as_doc_text` (pytest node id, verified passing when recorded)
- `tests/test_lang.py::TestCSharp::test_csharp_no_block_comment_type_split` (pytest node id, verified passing when recorded)
- `tests/test_lang_conformance_gate.py::TestCSharpCapabilityConformance::test_csharp_registered_capabilities_pass` (pytest node id, verified passing when recorded)
- `tests/test_lang_conformance_gate.py::TestCSharpCapabilityConformance::test_csharp_broken_continuation_fixture_is_caught_not_rubber_stamped` (pytest node id, verified passing when recorded)
- `tests/test_lang_conformance_gate.py::TestCSharpCapabilityConformance::test_csharp_no_symbols_fixture_is_caught_not_rubber_stamped` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 14 passed (from 14 evidence id(s))
- gates: 17 error(s), 584 warning(s), 851 waived
- error-findings: COV004@tickets/T-2195/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-2244/attachments/01-t-2244-audit-safe-to-repoint-split-test-typecheck-safe-now-lint-blocked-by-newly-found-t-2387-not-t-2359-format-lint-fix-blocked-by-both-test-fast-stays-raw.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, COV004@tickets/T-2328/attachments/02-third-reproduction-t-2323-confirmed-workaround-pre-commit-the-file-yourself-before-land.md, COV004@tickets/T-2328/attachments/03-clarification-titled-work-loss-defect-remains-open-carried-by-t-2351.txt, COV004@tickets/T-2350/attachments/01-diagnosis-timing-visibility-race-not-identity-matching-both-candidate-fix-files-leased-by-t-2351-no-edit-attempted.md, COV004@tickets/T-2543/attachments/01-class-a-options-and-measured-costs-t-2377-survey.md, CYCLE001@src/frob/__init__.py, DOC006@docs/guides/coordinator-scripts.md, DOC006@docs/modules/gates.md, DOC006@tickets/T-2886/ticket.md, DOC008@docs/commands/check.md, I001@/home/logan/projects/frob/.claude/worktrees/t-1604-series/tests/unit/verify/test_backpressure.py, TICK004@tickets.md
