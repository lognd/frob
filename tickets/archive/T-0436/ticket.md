---
id: T-0436
title: 'DOC004 unbound-code-block heuristic: flag fenced code blocks in docs that
  reference frob commands/symbols but are unbound (drift-prone)'
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
- tests/
- docs/modules/gates.md
- docs/commands/exports.md
- docs/guides/extending/sys-export-formats.md
- docs/modules/logging.md
- frob.toml
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_docblocks_gate.py::TestPythonNamespace::test_python_import_of_nonexistent_symbol_is_stale
- tests/test_docblocks_gate.py::TestPythonNamespace::test_unanchored_but_valid_import_warns_unbound
- tests/test_docblocks_gate.py::TestPythonNamespace::test_waive_doc004_suppresses
- tests/test_docblocks_gate.py::TestPythonNamespace::test_package_name_differs_from_directory_name
- tests/test_docblocks_gate.py::TestRustNamespace::test_rust_use_of_missing_item_is_stale
designated_repro_test: null
threat: null
component: null
---
User (2026-07-20): add a SIMPLE HEURISTIC check for unbound code blocks in docs. Code blocks in .md docs are the highest-drift-risk prose -- literal code/commands that silently go stale (e.g. README once showed removed commands; a python example importing a renamed symbol). Nothing binds them, so drift is invisible. SIMPLE HEURISTIC (keep it lightweight, per the user): scan every tracked .md doc for fenced code blocks; for each block that references frobs OWN surface, flag if UNBOUND: (a) CONSOLE/BASH blocks (```console / ```bash / ```sh / ```text) -- extract `frob <subcommand>` tokens; a subcommand NOT in the live argparse registry (frob --help) is STALE -> flag (catches `frob edit`/`frob mission`-class removed-command drift); (b) PYTHON blocks (```python / ```py) -- extract `from frob.X import Y`, `import frob.X`, and `frob.X.Y(` dotted paths; a path that does NOT resolve to a real symbol in the graph is STALE -> flag; (c) the CORE UNBOUND signal (WARN) -- a code block that references frob code/commands but has NO nearby binding directive (no frob:doc/frob:describes/frob:tests within the block or its immediately-preceding lines) -> flag as "unbound code block: not anchored, so drift will not be detected". Two tiers: stale-reference (a named command/symbol does not exist -> higher severity, real drift already present) vs unbound-but-currently-valid (WARN advisory -- add an anchor or it will drift silently). Deliberately HEURISTIC/conservative: only flag blocks that clearly reference frobs own commands/frob.* symbols (skip generic shell, third-party code, pseudo-code) to keep the false-positive rate low (the REF001-lesson -- a noisy gate gets blanket-waived). Waivable (frob:waive DOC004) for an intentional illustrative-only block. Ships per-project (T-0406). Acceptance: a doc block showing `frob edit` (removed) is flagged stale; a python block importing a nonexistent frob symbol is flagged; a real, unanchored `frob check` example warns unbound; an anchored/verified block passes; a generic non-frob shell block is NOT flagged. Run it on frobs own docs and disposition what it finds (fix stale, anchor real, waive illustrative).

REFINEMENT 1 (user): do NOT isolate to frobs own commands/symbols. Generalize to THE PROJECTs own code surface so it works in ANY frob-enabled repo (per-project, T-0406) -- resolve doc-block references against the graph + a configurable command source (frob.toml entry-point declaration), not a hardcoded frob-command list; frob is one instance. REFINEMENT 2 (user): PROMINENTLY WAIVABLE (frob:waive DOC004) for genuinely EXTERNAL (third-party library usage) or pure INSTRUCTIONAL/illustrative blocks the heuristic cannot confidently classify -- an intentional external example must be cleanly waivable, never a forced false positive. REFINEMENT 3 (user): NOT PYTHON-ONLY -- cover ALL languages (Python/Rust/TS/JS/C/C++/...) and must key on the projects ACTUAL PACKAGE/CRATE NAMES, which differ from directory names. Derive the projects own import namespaces from the LANGUAGE MANIFESTS: Python pyproject.toml [project.name] + the importable package(s) under src/; Rust Cargo.toml [package].name AND [workspace].members SUBCRATES (each subcrate is its own crate namespace); TS/JS package.json name; etc. Example: logand.app is packaged as logandapp_backend (NOT the dir name) -- a Rust `use logandapp_backend::foo` references the project (check foo resolves), while `use tokio::spawn` is external (skip/waivable). The manifest-derived, per-language project-namespace set is what distinguishes references-to-OUR-code (check they resolve -> stale if not) from external-library (skip). Acceptance additions: a Rust doc block `use <workspace-subcrate>::missing` is flagged stale; a `use <external-crate>::x` block is NOT flagged (or waivable); a project whose package name != dir name (logandapp_backend) is handled via its Cargo/pyproject manifest, not the dir name; TS/JS import of a project package vs a node_modules dep are distinguished via package.json.