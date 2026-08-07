## Done report

Changed:
strata-core/src/parse/mod.rs::Parser.parse_access_attr (new)
strata-core/src/parse/mod.rs::Parser.parse_node (access clause wired in)
strata-core/src/parse/mod.rs::Parser.parse_store (access clause wired in)
strata-core/src/parse/mod.rs::Parser.parse_resource (new)
strata-core/src/parse/mod.rs::Parser.parse_program (resource keyword dispatch)
strata-core/src/parse/mod.rs::ModuleAst.resources (new field)
src/frob/strata/_ast.py::ResourceDecl (new)
src/frob/strata/_ast.py::Module.resources (new field)
src/frob/strata/_access.py (new module): AccessMode, NodeAccess, ResourceContentionViolation, ResourceContentionReport, node_access_declarations, mode_conflict, resource_contention_violations, SYS_UNARBITRATED_MODE_CONFLICT
src/frob/strata/__init__.py (export the new symbols; aliased ResourceContentionReport/Violation as AccessResourceContentionReport/Violation to avoid colliding with _contention.py's SYS203 pair)
docs/strata/host.md (new "Resource access modes (T-0700)" section)
docs/strata/surface.md (Module AST bullet updated: +resources)
docs/guides/extending/strata-surface-grammar.md (worked-example addendum for this ticket's construct+clause addition)
editors/vscode-strata/syntaxes/strata.tmLanguage.json (declaration-keywords: +resource; clause-keywords: +access/arbitrated_by/lock/mode, and +bin_path -- a pre-existing T-0629 gap this ticket's own drift-lock run surfaced, fixed in the same pass since it's a one-token entry in a file already in scope)

Grammar added:
- `access "RESOURCE" mode MODE` on node/store (MODE closed vocabulary read|append|alpha|write|exclusive, validated at parse time), direct-attr-push to `access=<resource>:<mode>` (T-0629 bin_path precedent -- no NodeDecl/StoreDecl field threaded through _ast.py/_elaborate.py/_infra.py).
- `resource ID { arbitrated_by NODE | lock "NAME" }` top-level construct (at most one of the two, parse error otherwise); lands on the new `Module.resources` field (`_ast.py::ResourceDecl`) since a resource has no accessor of its own to desugar an attr onto.
- Compatibility matrix (`_access.py::mode_conflict`): only read+read and read+alpha are safe; alpha+alpha, any write/append/exclusive pairing (including against itself) conflicts -- matches the ticket's exact matrix, append/exclusive folded in as write-like (documented judgment call).
- Contention proof (`_access.py::resource_contention_violations`, new rule SYS204 "unarbitrated mode conflict"): every conflicting accessor PAIR of the same resource fires fail-closed unless the resource declares an arbiter (arbitrated_by or lock) -- matches the acceptance criterion exactly (verified manually end-to-end via parse_module -> elaborate -> resource_contention_violations, and via 7 dedicated pytest cases).

State: T-0700 acceptance criterion is met at the MODEL level (grammar + read-back + compatibility-matrix + fail-closed contention proof, all with tests). Two things were deliberately NOT done in this pass, disclosed rather than silently dropped:
1. CLI dispatch (`src/frob/app/sys_runner.py`) and the T-0174 `MULTI_INSTANCE_WAIVER_FAMILIES` waiver channel (`_waive.py`) were not wired -- both are shared surfaces the dispatch prompt flagged as a concurrent sibling's obligation-batch territory; `resource_contention_violations` is a pure, fully-tested function ready to be wired in. This is a disclosed, deliberate scope cut, not an oversight.
2. T-0701 (code-level mode-conformance enforcement -- whether a node's actual code obeys its declared mode) is explicitly a separate, blocked_by-T-0700 ticket and out of this ticket's scope per the ticket body itself.

Found while working (both filed, out of my ticket's scope, not fixed here):
- T-0955: pre-existing, unrelated golden/drift-lock drift in `tests/unit/strata/test_export_golden.py` (test_k8s/test_seccomp/test_iam) and `tests/system/test_frob_self_model.py::TestFrobSelfModel::test_parses_and_elaborates` (node count 16 vs hardcoded 15) -- both trace to frob's own self-modeled design gaining a `natives` node whose golden fixtures/hardcoded counts were never regenerated. Confirmed via `git status`/diff that none of my files touch these; scope of the draft ticket covers both files.

Evidence: 27 ids recorded and bound to acceptance[0] via `frob ticket evidence T-0700 ... --accepts 0` (9 Rust `cargo test --release` node ids under `strata-core/src/parse/mod.rs::tests`, 16 pytest node ids under `tests/unit/strata/test_access.py`, 2 under `tests/unit/test_strata_tmlanguage.py`). All 27 observed passing:
- `cargo test --release` (PYO3_PYTHON/LD_LIBRARY_PATH set to the worktree's own .venv python3.11): 132 passed, 0 failed (123 pre-existing + 9 new).
- `uv run pytest tests/unit/strata/test_access.py tests/unit/test_strata_tmlanguage.py -p no:cacheprovider -q`: 28 passed (16 + 12; 2 of the tmlanguage tests are the drift-lock bidirectional checks, the rest are pre-existing tmlanguage coverage tests unaffected by this change).
- `uv run pytest tests/unit/strata/ -p no:cacheprovider -q` (deselecting the 3 pre-existing unrelated golden failures above): all green.

Filed: T-0955 (pre-existing export-golden/self-model drift-lock drift, see above; scope covers both affected test files)

Gates: `frob check --ticket T-0700 --only <lint|static|gates-fast|gates-native|gates-security>` (the section 3b chunked loop) all clean for my scope -- `lint` shows only pre-existing unrelated ty/ruff-format issues in `tests/test_gates.py`/`src/frob/arch/_lock_ordering.py`/`tests/unit/test_arch.py` (confirmed untouched by `git status`); `static` shows only pre-existing frob-exports advisories elsewhere (none introduced by `_access.py`, which is fully exported); `gates-fast`/`gates-native`/`gates-security` all report `pass` on every gate id after fixing (in order surfaced): missing COV001/frob:doc anchors, wrong test-class name in a frob:tests directive (DRIFT002), a missing INV006 waiver (module docstring precedent from `_ssot.py`/`_contention.py`), a stale PRE001 pre-work sweep (re-ran `frob ticket sweep T-0700`), and a SCOPE001 for `docs/guides/extending/strata-surface-grammar.md` (added via `frob ticket scope T-0700 --add`, since AFFECT001 correctly flagged `Parser.parse_program`'s affects-closure doc). `git diff main --diff-filter=D --stat` is empty (deletion-filter check clean).

### Changed
(no changed files detected)

### Evidence
- `strata-core/src/parse/mod.rs::tests::parses_node_access_clause` (pytest node id, verified passing when recorded)
- `strata-core/src/parse/mod.rs::tests::parses_store_access_clause` (pytest node id, verified passing when recorded)
- `strata-core/src/parse/mod.rs::tests::parses_all_access_modes` (pytest node id, verified passing when recorded)
- `strata-core/src/parse/mod.rs::tests::error_access_rejects_unknown_mode` (pytest node id, verified passing when recorded)
- `strata-core/src/parse/mod.rs::tests::error_access_requires_mode_keyword` (pytest node id, verified passing when recorded)
- `strata-core/src/parse/mod.rs::tests::parses_resource_with_arbitrated_by` (pytest node id, verified passing when recorded)
- `strata-core/src/parse/mod.rs::tests::parses_resource_with_lock` (pytest node id, verified passing when recorded)
- `strata-core/src/parse/mod.rs::tests::parses_bare_resource_with_no_arbiter` (pytest node id, verified passing when recorded)
- `strata-core/src/parse/mod.rs::tests::error_resource_rejects_both_arbitrated_by_and_lock` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_access.py::TestNodeAccessDeclarations::test_reads_access_attrs` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_access.py::TestNodeAccessDeclarations::test_no_access_attrs_is_empty` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_access.py::TestNodeAccessDeclarations::test_unrecognized_mode_fails_closed` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_access.py::TestModeConflict::test_read_read_is_safe` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_access.py::TestModeConflict::test_read_alpha_is_safe` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_access.py::TestModeConflict::test_alpha_alpha_conflicts` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_access.py::TestModeConflict::test_write_conflicts_with_anything` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_access.py::TestModeConflict::test_exclusive_conflicts_with_everything_including_itself` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_access.py::TestModeConflict::test_append_conflicts_with_anything` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_access.py::TestResourceContentionViolations::test_two_writers_no_arbiter_fires` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_access.py::TestResourceContentionViolations::test_arbitrated_by_discharges` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_access.py::TestResourceContentionViolations::test_lock_discharges` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_access.py::TestResourceContentionViolations::test_read_only_modes_discharge_without_arbiter` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_access.py::TestResourceContentionViolations::test_bare_resource_declaration_with_no_arbiter_still_fires` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_access.py::TestResourceContentionViolations::test_single_accessor_never_fires` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_access.py::TestResourceContentionViolations::test_unrelated_resources_do_not_cross_conflict` (pytest node id, verified passing when recorded)
- `tests/unit/test_strata_tmlanguage.py::test_construct_keywords_match_parser_bidirectionally` (pytest node id, verified passing when recorded)
- `tests/unit/test_strata_tmlanguage.py::test_clause_keywords_covered_by_grammar` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 27 passed (from 27 evidence id(s))
- gates: 0 error(s), 4192 warning(s), 219 waived
- error-findings: none (measured, zero errors)
