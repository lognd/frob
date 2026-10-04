+++
id = "01M43A5DJT8XBQYEK36F0KSGKF"
title = "First-party Python adapter: language, comments, symbols, imports, calls, tests"
type = "story"
category = "in-progress"
priority = "high"
points = 8
parent = "01M43A5349M17PED730HKNM4VV"
reporter = "lognd"
created = "2026-10-04T11:18:09Z"
updated = "2026-10-04T11:32:00Z"
scope = ["crates/gob-languages/**", "crates/gob-symbols/**", "crates/gob-directives/src/comments.rs", "crates/frob-obligations/src/comments.rs", "crates/frob-check/tests/**", "docs/reference/fidelity.md", "Cargo.toml", "crates/gob-directives/src/scan.rs", "crates/gob-directives/src/bind.rs", "crates/frob-obligations/src/cov.rs", "crates/frob-tests/src/catalog.rs", "Cargo.lock", "crates/frob-tests/src/touched.rs"]

[[acceptance]]
text = "Given a Python file with a frob directive in a comment and a bare TODO, when frob check runs, then the directive binds to the item below and TODO001 fires"
bound = false

[[acceptance]]
text = "Given a Python package with pytest tests, when the symbol graph is built, then modules, classes, functions, imports, calls and test functions are present and COV001 sees which functions tests reach"
bound = false

[[acceptance]]
text = "Given a Python construct the adapter does not model, when check runs, then it is reported Unresolved, not clean"
bound = false
+++

Owner decision 2026-10-04: Python support first. 7 of the owner's 9 fleet repositories are Python-dominant, and today v2 reads Python as an opaque F0 file: a `# TODO` is unflagged, frob directives in Python comments are ignored, and no symbol, call or test is known (notes/review/v1-gap/C-features.md P-03).

Build the first-party Python adapter at the same fidelity the Rust adapter has (read docs/design/code-model.md, universal-model.md and the Rust adapter in gob-symbols as the model to match):
1. gob-languages: Language::Python (.py, .pyi), tree-sitter-python pinned the way the other grammars are; `#` comments in both comment scanners so directives, accepts and TODO001 work.
2. gob-symbols: a Python adapter producing units (modules, classes, functions, methods, nested), imports (import, from-import, relative), calls with qualifiers, decorators as attributes, docstrings for DOC rules, and test detection (pytest: test_ functions and Test classes in test files; unittest TestCase methods) so COV/TEST rules and frob test selection see Python tests.
3. Fidelity reported as for Rust; anything not modelled is Unresolved, never clean.
4. Fixtures: a small Python package with tests in the gob-symbols and frob-check test corpora, plus a run of frob check on it end to end.
