## Done report

Added `_imports_typescript`/`_imports_rust`/`_imports_kotlin` walkers to
`src/frob/lang/_extract.py`, mirroring `_imports_python`/`_imports_c_family`'s
shape, and registered them (plus `tsx` reusing the typescript walker, matching
the existing `_WALKERS`/`_walk_tsx` convention) in `_IMPORT_WALKERS`.
`extract_imports` previously returned an empty tuple for these three
languages -- a real gap T-2365's capability-conformance axis flagged as
KNOWN_GAP (`_capability_import_graph_status` in `src/frob/lang/_support.py`,
out of this ticket's declared scope).

Grammar shapes were confirmed directly against tree-sitter-language-pack
parses (typescript `import_statement`/`export_statement` with a `from
'...'` string child covers value imports, re-exports, and side-effect
imports uniformly; rust `use_declaration`'s non-keyword child covers plain,
aliased, and grouped `use` paths as one raw specifier per statement, mirroring
`_imports_c_family`'s "one specifier per statement" shape rather than
python's per-name expansion; kotlin `import_header`'s `identifier` child
covers plain, wildcard, and aliased imports).

Added `tests/unit/test_lang_primitives.py::test_extract_imports_typescript_rust_kotlin`
covering all three (scope widened via `frob ticket scope T-2408 --add
tests/unit/test_lang_primitives.py`, TEST001 evidence for the new code).

Disclosed cut: `src/frob/lang/_support.py::_capability_import_graph_status`
still hardcodes the `{"python", "c", "cpp"}` membership check rather than
reading `_IMPORT_WALKERS` keys directly, so the capability-conformance
registry will keep reporting typescript/rust/kotlin as KNOWN_GAP (citing
T-2408) even after this lands -- that file is not in this ticket's declared
scope. Not fixed here; flagging so whoever picks up the registry-side
follow-up does not have to re-discover it.

Filed: T-2494 (capability_import_graph_status hardcodes language set,
stale after T-2408).

### Changed
```
 src/frob/lang/_extract.py          | 91 ++++++++++++++++++++++++++++++++++++++
 tests/unit/test_lang_primitives.py | 27 +++++++++++
 tickets/T-2408/done-report.md      | 52 ++++++++++++++++++++++
 tickets/T-2408/ticket.md           | 14 +++++-
 tickets/T-draft-612a25f7/ticket.md | 43 ++++++++++++++++++
 5 files changed, 226 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_lang_primitives.py::test_extract_imports_typescript_rust_kotlin` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/gates/_refs_schema.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, RENDER001@src/frob/release/_cli.py, SEC110@.claude/hooks/root-write-guard.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md
