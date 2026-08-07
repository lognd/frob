---
id: T-0437
title: 'Doc-pointer resolution gate: every doc reference of a RECOGNIZED resolvable
  shape must resolve (hardened closed-set, not fuzzy ''seems to point'')'
state: done
kind: feature
origin: human
created: '2026-07-20'
priority: medium
parent: T-0435
tier: ticket
sprint: null
scope:
- src/frob/gates/
- src/frob/graph/
- docs/
- frob.toml
- tests/test_docptr_gate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_docptr_gate.py
  reason: T-0437 new-rule acceptance fixture + unit tests for DOC006
  actor: logan
  at: '2026-07-27'
evidence:
- tests/test_docptr_gate.py::TestDoc006FilePath::test_missing_path_flagged
- tests/test_docptr_gate.py::TestDoc006FilePath::test_real_path_passes
- tests/test_docptr_gate.py::TestDoc006FilePath::test_unrecognized_prose_not_flagged
- tests/test_docptr_gate.py::TestDoc006FilePath::test_dot_frob_runtime_path_not_flagged
- tests/test_docptr_gate.py::TestDoc006DocAnchor::test_missing_anchor_flagged
- tests/test_docptr_gate.py::TestDoc006DocAnchor::test_real_anchor_passes
- tests/test_docptr_gate.py::TestDoc006Cli::test_nonexistent_subcommand_flagged
- tests/test_docptr_gate.py::TestDoc006Cli::test_nonexistent_flag_flagged
- tests/test_docptr_gate.py::TestDoc006Cli::test_real_command_passes
- tests/test_docptr_gate.py::TestDoc006Config::test_bogus_section_flagged
- tests/test_docptr_gate.py::TestDoc006Config::test_real_section_passes
- tests/test_docptr_gate.py::TestDoc006Symbol::test_nonexistent_symbol_flagged
- tests/test_docptr_gate.py::TestDoc006Symbol::test_real_symbol_passes
- tests/test_docptr_gate.py::TestDoc006Symbol::test_module_dunder_init_and_all_pass
- tests/test_docptr_gate.py::TestDoc006Symbol::test_class_attribute_chain_not_flagged
- tests/test_docptr_gate.py::TestDoc006Waive::test_waive_suppresses
- tests/test_docptr_gate.py::TestDoc006TestsTargetShape::test_double_separator_target_flagged
- tests/test_docptr_gate.py::TestDoc006TestsTargetShape::test_single_separator_target_not_flagged
designated_repro_test: null
acceptance:
- text: given frob.gates._docptr.doc006_gate did not exist before this change (a doc
    mentioning src/frob/gone.py, frob check --nonexistent-flag, [bogus.section], or
    docs/missing.md#x could not FAIL any check), when the gate is wired into frob
    check via the "docblocks" job (frob.gates.__init__._build_jobs), then those same
    fixtures now FAIL frob.gates._docptr.doc006_gate (DOC006, tests/test_docptr_gate.py)
    while a real path/command/flag/symbol/anchor PASSES clean and an unrecognized
    prose token is never flagged -- proving the rule fires through the production
    frob check invocation, not just a pure-function unit test
  evidence:
  - tests/test_docptr_gate.py::TestDoc006FilePath::test_missing_path_flagged
  - tests/test_docptr_gate.py::TestDoc006FilePath::test_real_path_passes
  - tests/test_docptr_gate.py::TestDoc006FilePath::test_unrecognized_prose_not_flagged
  - tests/test_docptr_gate.py::TestDoc006FilePath::test_dot_frob_runtime_path_not_flagged
  - tests/test_docptr_gate.py::TestDoc006DocAnchor::test_missing_anchor_flagged
  - tests/test_docptr_gate.py::TestDoc006DocAnchor::test_real_anchor_passes
  - tests/test_docptr_gate.py::TestDoc006Cli::test_nonexistent_subcommand_flagged
  - tests/test_docptr_gate.py::TestDoc006Cli::test_nonexistent_flag_flagged
  - tests/test_docptr_gate.py::TestDoc006Cli::test_real_command_passes
  - tests/test_docptr_gate.py::TestDoc006Config::test_bogus_section_flagged
  - tests/test_docptr_gate.py::TestDoc006Config::test_real_section_passes
  - tests/test_docptr_gate.py::TestDoc006Symbol::test_nonexistent_symbol_flagged
  - tests/test_docptr_gate.py::TestDoc006Symbol::test_real_symbol_passes
  - tests/test_docptr_gate.py::TestDoc006Symbol::test_module_dunder_init_and_all_pass
  - tests/test_docptr_gate.py::TestDoc006Symbol::test_class_attribute_chain_not_flagged
  - tests/test_docptr_gate.py::TestDoc006Waive::test_waive_suppresses
  - tests/test_docptr_gate.py::TestDoc006TestsTargetShape::test_double_separator_target_flagged
  - tests/test_docptr_gate.py::TestDoc006TestsTargetShape::test_single_separator_target_not_flagged
threat: null
component: null
---
User (2026-07-20): account for anything that looks like a tool usage/guide, and any documentation that SEEMS to point to something -- and HARDEN the wishy-washy part. THE HARDENING: do not try to detect fuzzy "seems to point to X" intent (unhardenable, high FP). Instead define a CLOSED SET of RECOGNIZED, RESOLVABLE POINTER SHAPES and only fire when a pointer of a known shape targets something that does NOT exist. This converts "seems to point" into a mechanical, resolvable check with a naturally-low FP rate (an unrecognized shape is simply not checked). POINTER KINDS (each detectable + resolvable against the real project): (1) FILE/PATH -- a repo-relative path (src/frob/foo.py, docs/bar.md, frob.toml) mentioned in a code span/block/link must EXIST; (2) CLI INVOCATION / TOOL-GUIDE -- `<project-cli> <subcommand>` and `--flag`/`-x` options against the projects real argparse/command source (frob is one instance; per-project via a configurable command source) -- a nonexistent subcommand or flag is stale; (3) CONFIG REFERENCE -- a `[section]` or `[section].key` or a frob.toml/pyproject/Cargo key referenced must be a REAL config key of that manifest/schema; (4) CODE SYMBOL -- a dotted path / import / use (module.Class.method, from X import Y, use crate::x) resolves in the graph against the projects manifest-derived namespaces (see T-0436: Rust workspace subcrates, pyproject/package.json package names != dir names; external namespaces skipped); (5) DOC-ANCHOR LINK -- a docs/x.md#anchor (or a frob:doc/frob:describes anchor target) must exist. SCOPE: inline code spans AND fenced code blocks AND markdown links AND tool-guide prose ("run `X`", "add `[section]` to frob.toml", "the `--foo` flag", "see `docs/bar.md`"). CONSERVATISM: only a pointer matching a recognized shape whose target is DEFINITIVELY resolvable-or-refutable is checked; an unrecognized/ambiguous token is NOT flagged (the hardening). PROMINENTLY WAIVABLE (frob:waive) for intentional external/illustrative/future-facing pointers. Ships per-project (T-0406), all languages. T-0436 (unbound/stale CODE BLOCKS) is ONE INSTANCE of this; this ticket is the general doc-pointer-resolution gate (the north-star doc-drift check, cf T-0325). Acceptance: a doc mentioning `src/frob/gone.py` (nonexistent) flagged; `frob edit`/`--nonexistent-flag` flagged; a `[bogus.section]` frob.toml reference flagged; a `docs/missing.md#x` link flagged; a real path/command/flag/symbol/anchor passes; an unrecognized prose token NOT flagged; external pointers waivable. Run on frobs own docs, report FP rate, disposition honestly.