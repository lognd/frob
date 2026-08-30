## Done report

Adds Zig as a registered `frob.lang` language. `tree-sitter-language-pack`'s
"zig" grammar exposes NO named fields at all (verified interactively) --
so `_walk_zig.py` follows `_walk_kotlin.py`'s positional/type-based shape
(`_zig_child_of_type`), not csharp/java's field-based one.

Changed:
src/frob/lang/_walk_zig.py (new)
src/frob/lang/_extract.py::COMMENT_TYPES / _WALKERS / _imports_zig / _IMPORT_WALKERS
src/frob/lang/__init__.py::_EXTENSION_TABLE (.zig)
src/frob/gates/_lang_conformance.py::_CAPABILITY_FIXTURE_SOURCES / _CAPABILITY_FIXTURE_EXTENSIONS
src/frob/lang/_support.py (widened `_PENDING_FACET_WIRING_TICKETS` to add zig)
frob.toml ([[test.runner]] language="zig")
tests/fixtures/lang/sample.zig (new)
tests/test_lang.py::TestZig (new)
tests/test_lang_conformance_gate.py::TestZigCapabilityConformance (new)
docs/modules/lang.md (publicness table, per-language walker-module list,
  per-language walker notes, contract-section note)

PUBLICNESS (ticket's own required decision): `pub` is Zig's explicit,
opt-in visibility marker -- ABSENT means private (rust's "enumerate the
public set" shape, the opposite of kotlin's default-public rule). A
Zig-specific grammar quirk this decision had to account for: `pub` is a
bare SIBLING token immediately preceding the `Decl` it marks, never a
child of that `Decl` (unlike every prior adapter's own modifier-scan
shape) -- `_zig_visit` tracks a `pending_pub` flag while iterating a
container's children instead. Verified with test_walks_top_level_function
(pub) / test_function_without_pub_is_not_public (bare).

COMPTIME BLOCKS (ticket's own required decision): a top-level `comptime {
... }` block is a bare, unnamed side-effecting block with no declaration
name of its own -- never walked for symbols, a disclosed limitation
mirroring how `_walk_python.py` never walks a function body's nested
closures. Verified with test_comptime_block_is_not_walked_for_symbols.

ERROR UNIONS IN SIGNATURES (ticket's own required decision): a fallible
function's `!ReturnType` marker is an ordinary positional child of
`FnProto` -- needs no special handling, `sig_tokens` captures it
uniformly, so `mayFail() !i32` and a plain `() i32` correctly produce
different signatures. Verified with test_error_union_return_type_is_
captured_in_signature.

DOC COMMENTS (ticket's own required decision): `///` gets its OWN node
type, `doc_comment`, genuinely distinct from `line_comment` (`//`/`//!`)
-- unlike every prior C-style-comment adapter where doc and plain
comments share one or two types. `COMMENT_TYPES` (general leaf
extraction, `pf.comments`) covers both; a private, narrower
`_ZIG_DOC_COMMENT_TYPES = {"doc_comment"}` is what `_zig_leading_doc`
passes to `_leading_doc_comment` for `doc_text` binding, so a plain `//`/
`//!` comment never counts as a symbol's doc text. Verified with
test_triple_slash_doc_comment_binds_as_doc_text (positive) and
test_plain_comment_does_not_bind_as_doc_text (negative control -- proves
the plain comment is still extracted as a RawComment via the wider set,
just never bound as doc_text).

struct/union -> CLASS, enum -> TYPE (mirrors `_walk_c.py`'s own
struct-vs-enum split); found by walking a `VarDecl`'s value-expression
wrapper chain (`ErrorUnionExpr` -> `SuffixExpr`) down to a `ContainerDecl`
-- verified with test_struct_and_method / test_enum_is_a_type_symbol.
`const`/`var` bindings map to `CONST` (Zig has no type-alias keyword
distinct from an ordinary value binding) -- verified with test_top_level_
const_is_a_const_symbol. `@import("...")`'s string argument is the
import statement -- verified with test_import_builtin_is_extracted.

Directive DSL / obligation graph: unlike CUDA (T-1602's own disclosed
C-comment-splice quirk), Zig's `//` grammar does NOT merge a backslash-
continued two-physical-line comment into one node (verified
interactively) -- a real `// frob:tests \` / `// <target>` continuation
folds correctly, proven end to end by test_zig_broken_continuation_
fixture_is_caught_not_rubber_stamped (the MUST-FAIL control: dropping the
continuation's second physical line makes directive_parse fail, same
shape as csharp/java's own continuation controls).

Capability conformance (T-1599's 6-of-7 axis): symbol_walk, publicness,
doc_extract, directive_parse, call_graph, import_graph are ALL
IMPLEMENTED and behaviorally verified -- Zig calls are parenthesized
(`foo()`), so no call_graph KNOWN_GAP is needed. test_discovery stays
structural-only (no bounded, offline-safe Zig test-runner toolchain
integration exists yet, same disclosed posture as every prior non-
python/rust language).

Positive/negative controls:
- Positive (must-pass): tests/fixtures/lang/sample.zig -- pub/non-pub
  functions, struct with a pub and a non-pub method, enum, top-level
  const, error-union return type, triple-slash doc comment, plain
  comment (not bound as doc), comptime block (not walked).
- Positive (must-fail #1): test_zig_broken_continuation_fixture_is_
  caught_not_rubber_stamped -- dropped continuation line fails
  directive_parse.
- Positive (must-fail #2): test_zig_no_symbols_fixture_is_caught_not_
  rubber_stamped -- empty fixture fails symbol_walk.

FACETS-wiring gap (mirrors T-2906's bash/csharp and T-1601/T-1602's
java/cuda precedent): zig's capability/dup/docblock facets are not yet
wired into frob.vet._capability_registry / frob.dup._exhaustiveness /
frob.gates._docblocks. Filed a follow-up ticket (T-3513,
renumbers at land) while working this ticket and cited it via the
already-widened `_PENDING_FACET_WIRING_TICKETS` mapping in `_support.py`
(now covering java/T-3492, cuda/T-3493, and zig's own new ticket).

Evidence: 14 node ids bound via `frob ticket evidence T-1603`, all
passing via `uv run pytest -q -p no:xdist tests/test_lang.py -k Zig
tests/test_lang_conformance_gate.py -k Zig` (20 passed). Broader run
(before this ticket's own coordinator-requested T-3495 detour):
`uv run pytest -q -p no:xdist tests/test_lang.py
tests/test_lang_conformance_gate.py tests/test_lang_support.py`,
excluding the same 4 pre-existing strata-native-unavailable failures
this fresh worktree carried before `make core`, 247 passed.

Gates: `frob check --only docblocks --only lang_conformance --only
lang_project_conformance` -- gate:LANG clean (0 errors, 27 warnings, 5 of
them the newly-added zig facet WARNs, all verifying against the
T-3513 citation). Every FAIL in the wider run (DOC/DRIFT/WAIVE)
traces to files outside this ticket's touched set -- same pre-existing
findings T-1601/T-1602's own done-reports already confirmed unrelated.

Series note: while working this ticket, the coordinator raised a
possible CI regression from T-1601's Java land (a 99% CI tail stall) and
asked for an A/B measurement plus, regardless of outcome, work on the
durable fix. Both were completed as a detour before returning to finish
and land this ticket: the A/B showed NO Java regression (single-test
timings 73.9s parent vs 52.3s child, e030f5ed3971~1 vs e030f5ed3971), and
the durable fix (T-3495, a session-scoped shared self-scan fixture)
landed separately at cc67e4c12e3c, cutting the affected 5-test group's
wall time from 449.9s to 105.7s (~4.3x). See T-3495's own done-report for
the full measurement and fix detail; this ticket's own scope/evidence/
gates above are unaffected by that detour.

Filed:
- T-3513 (renumbers at land) -- wire zig into vet/dup/docblock
  capability facets, mirroring T-2906's bash/csharp and T-1601/T-1602's
  java/cuda follow-ups exactly.

### Changed
```
 tickets/T-1603/ticket.md           | 17 ++++++++++++++++-
 tickets/T-3513/ticket.md | 32 ++++++++++++++++++++++++++++++++
 2 files changed, 48 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_lang.py::TestZig::test_walks_top_level_function` (pytest node id, verified passing when recorded)
- `tests/test_lang.py::TestZig::test_function_without_pub_is_not_public` (pytest node id, verified passing when recorded)
- `tests/test_lang.py::TestZig::test_struct_and_method` (pytest node id, verified passing when recorded)
- `tests/test_lang.py::TestZig::test_enum_is_a_type_symbol` (pytest node id, verified passing when recorded)
- `tests/test_lang.py::TestZig::test_top_level_const_is_a_const_symbol` (pytest node id, verified passing when recorded)
- `tests/test_lang.py::TestZig::test_error_union_return_type_is_captured_in_signature` (pytest node id, verified passing when recorded)
- `tests/test_lang.py::TestZig::test_triple_slash_doc_comment_binds_as_doc_text` (pytest node id, verified passing when recorded)
- `tests/test_lang.py::TestZig::test_plain_comment_does_not_bind_as_doc_text` (pytest node id, verified passing when recorded)
- `tests/test_lang.py::TestZig::test_comptime_block_is_not_walked_for_symbols` (pytest node id, verified passing when recorded)
- `tests/test_lang.py::TestZig::test_zig_two_comment_node_types` (pytest node id, verified passing when recorded)
- `tests/test_lang.py::TestZig::test_import_builtin_is_extracted` (pytest node id, verified passing when recorded)
- `tests/test_lang_conformance_gate.py::TestZigCapabilityConformance::test_zig_registered_capabilities_pass` (pytest node id, verified passing when recorded)
- `tests/test_lang_conformance_gate.py::TestZigCapabilityConformance::test_zig_broken_continuation_fixture_is_caught_not_rubber_stamped` (pytest node id, verified passing when recorded)
- `tests/test_lang_conformance_gate.py::TestZigCapabilityConformance::test_zig_no_symbols_fixture_is_caught_not_rubber_stamped` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 14 passed (from 14 evidence id(s))
- gates: 22 error(s), 4111 warning(s), 871 waived
- error-findings: COV003@tests/unit/test_scaffold_project.py, DEPR006@frob-deprecated-baseline.lock.json, DOC006@changelog.d/T-2691.md, DOC006@tickets/T-3489/ticket.md, DOC007@src/frob/verify/_bisect.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT002@src/frob/verify/_bisect.py, E501@/home/logan/projects/frob/.claude/worktrees/t-1603/src/frob/lang/_walk_zig.py, LARGE001@.claude/hooks/root-write-guard.py, LARGE001@src/frob/arch/_mayraise.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PRE001@tickets/T-1603, REL001@src/frob/__init__.py, TICK004@tickets.md, WAIVE009@src/frob/arch/_normalized.py, WAIVE011@frob-ratchet.lock.json, WIRE002@src/frob/app/ticket_runner/_land_cmd.py, WIRE002@src/frob/gates/_arch.py, WIRE002@src/frob/gates/_coverage_sites.py, WIRE002@src/frob/gates/_render_lint.py, WIRE002@tests/unit/test_new_ticket_scope_overlap_warning.py
