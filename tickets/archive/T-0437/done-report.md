## Done report

Changed:
src/frob/gates/_docptr.py (new: doc006_gate, five pointer-kind resolvers,
frob:tests target-form check)
src/frob/gates/__init__.py (_KNOWN_GATE_RULES += DOC006; docblocks job now
also calls doc006_gate)
tests/test_docptr_gate.py (new, 18 tests)
docs/modules/gates.md (DOC006 table row + "DOC006 doc-pointer resolution
gate T-0437" section)
docs/design/registry/check-coverage.yaml (CHK-GATE-DOC006 entry;
gate_rule_total 118 -> 119)
tickets.md (T-0437 acceptance criterion + scope += tests/test_docptr_gate.py)

Rule id: DOC006 (gate name `docblocks`, alongside DOC004/DOC005), WARN
severity at turn-on per the T-0688 new-gate-at-WARN precedent (see below).

Recognized shapes (closed set, over doc PROSE -- inline code spans +
markdown links, not fenced code blocks, which stay DOC004's job):
1. FILE/PATH -- repo-relative path or well-known bare manifest basename
   (frob.toml/pyproject.toml/Cargo.toml/package.json) must be tracked.
   `.frob/*` is exempted (real but deliberately untracked runtime
   artifact, round-2 fix after dogfooding).
2. CLI INVOCATION -- `<prog> <subcommand...>`/`--flag` against the live
   [[docblocks.commands]]-configured argparse registry (same source
   DOC004/DOC005 already walk); flags checked via a new leaf-parser walk
   (`_leaf_parser`) since DOC004's `_console_trees` only carries the
   subcommand shape, not options.
3. CONFIG REFERENCE -- `[section]`/`[section.key]` against this project's
   loaded frob.toml.
4. CODE SYMBOL -- dotted `module.Class.method` against manifest-derived
   python namespaces + the real graph (reuses
   frob.gates._docblocks's module-map/symbol-name/reexport helpers).
   Conservative beyond one level: `module.__init__`/`module.__all__` pass
   (module boundary reference), and a `module.Class.attr`-shaped chain one
   level past what the resolver can prove/refute is silently skipped
   (round-2 fix) rather than false-flagged STALE.
5. DOC-ANCHOR LINK -- `docs/x.md#anchor`, file existence + real
   heading/`<a id>` slug (mirrors DOC002's `_doc_anchor_slugs`).
6. frob:tests target-form hardening (the T-0940/T-0945 DRIFT002 ask): any
   `frob:tests` edge (source-wide, not doc-scoped) whose target contains a
   SECOND `::` (pytest's `Class::method` separator vs this graph's single
   `::` + dotted `Class.method`) is flagged directly.

Repo violation count at turn-on (WARN, `frob check --ticket T-0437 --only
gates-fast`, real numbers from the JSON run, not estimated):
- First pass (before the round-2 false-positive fixes below): 879 DOC006
  findings repo-wide.
- After fixing three FP classes found dogfooding frob's own docs (.frob/*
  runtime paths, module.__init__/__all__, class-attribute chains one level
  deep): 721 DOC006 findings repo-wide -- an ~18% reduction from three
  targeted fixes, all now covered by regression tests
  (TestDoc006FilePath::test_dot_frob_runtime_path_not_flagged,
  TestDoc006Symbol::test_module_dunder_init_and_all_pass,
  TestDoc006Symbol::test_class_attribute_chain_not_flagged).
- Kind breakdown at 879 (before fixes): file/path 614, config reference
  142, code symbol 81, cli invocation 22, doc-anchor link 20. The
  remaining 721 are disclosed as pre-existing drift this WARN-severity
  turn-on surfaces, not fixed in this ticket's scope (per playbook section
  6/T-0688: a new gate turning on against existing violations ships WARN
  and reports the count, it does not obligate fixing every existing doc in
  the same change). A residual, not-yet-audited false-positive tail likely
  remains in the 721 (e.g. DOC004's own pre-existing `_resolve_command_chain`
  positional-argument-vs-subcommand conservatism, inherited unchanged,
  visible on `frob scaffold pool N`-shaped examples) -- flagged here
  honestly rather than claimed zero.

Ticket-scoped verification (frob check --ticket T-0437, chunked --only
loop per the playbook's mandatory pattern): lint clean (my files); static
clean (my files); gates-fast: 0 errors after fixes (COV/AFFECT/SCOPE/PRE/
REG/INV all cleared for this ticket's scope -- REG005's gate_rule_total
bumped 118->119, PRE001 cleared via `frob ticket sweep T-0437` after
scope+file changes, INV006 waived with a reason matching
frob.gates._docblocks's own T-0585 precedent); gates-native: 0 errors, all
PERF/ARCH/EXHAUST findings pre-existing and unrelated to this diff.

Evidence: 18 pytest node ids (all bound to acceptance criterion 0, see
`frob ticket show T-0437`), all collected and passing:
tests/test_docptr_gate.py::TestDoc006FilePath::test_missing_path_flagged
tests/test_docptr_gate.py::TestDoc006FilePath::test_real_path_passes
tests/test_docptr_gate.py::TestDoc006FilePath::test_unrecognized_prose_not_flagged
tests/test_docptr_gate.py::TestDoc006FilePath::test_dot_frob_runtime_path_not_flagged
tests/test_docptr_gate.py::TestDoc006DocAnchor::test_missing_anchor_flagged
tests/test_docptr_gate.py::TestDoc006DocAnchor::test_real_anchor_passes
tests/test_docptr_gate.py::TestDoc006Cli::test_nonexistent_subcommand_flagged
tests/test_docptr_gate.py::TestDoc006Cli::test_nonexistent_flag_flagged
tests/test_docptr_gate.py::TestDoc006Cli::test_real_command_passes
tests/test_docptr_gate.py::TestDoc006Config::test_bogus_section_flagged
tests/test_docptr_gate.py::TestDoc006Config::test_real_section_passes
tests/test_docptr_gate.py::TestDoc006Symbol::test_nonexistent_symbol_flagged
tests/test_docptr_gate.py::TestDoc006Symbol::test_real_symbol_passes
tests/test_docptr_gate.py::TestDoc006Symbol::test_module_dunder_init_and_all_pass
tests/test_docptr_gate.py::TestDoc006Symbol::test_class_attribute_chain_not_flagged
tests/test_docptr_gate.py::TestDoc006Waive::test_waive_suppresses
tests/test_docptr_gate.py::TestDoc006TestsTargetShape::test_double_separator_target_flagged
tests/test_docptr_gate.py::TestDoc006TestsTargetShape::test_single_separator_target_not_flagged
(pytest tests/test_docptr_gate.py -q: 18 passed)

Filed: none (no out-of-scope discoveries requiring a new ticket; the
residual 721-count false-positive tail is disclosed above, not filed
separately, since it is this ticket's own turn-on debt, not a neighboring
bug).

Gates: `frob check --ticket T-0437` clean across lint/static/gates-fast/
gates-native (chunked --only loop, playbook section 3b); gates-security: 0 errors, all pre-existing PII/SEC advisories unrelated
to this diff.

### Changed
(no changed files detected)

### Evidence
- `tests/test_docptr_gate.py::TestDoc006FilePath::test_missing_path_flagged` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006FilePath::test_real_path_passes` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006FilePath::test_unrecognized_prose_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006FilePath::test_dot_frob_runtime_path_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006DocAnchor::test_missing_anchor_flagged` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006DocAnchor::test_real_anchor_passes` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006Cli::test_nonexistent_subcommand_flagged` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006Cli::test_nonexistent_flag_flagged` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006Cli::test_real_command_passes` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006Config::test_bogus_section_flagged` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006Config::test_real_section_passes` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006Symbol::test_nonexistent_symbol_flagged` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006Symbol::test_real_symbol_passes` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006Symbol::test_module_dunder_init_and_all_pass` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006Symbol::test_class_attribute_chain_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006Waive::test_waive_suppresses` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006TestsTargetShape::test_double_separator_target_flagged` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006TestsTargetShape::test_single_separator_target_not_flagged` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 18 passed (from 18 evidence id(s))
- gates: 0 error(s), 4964 warning(s), 220 waived
- error-findings: none (measured, zero errors)
