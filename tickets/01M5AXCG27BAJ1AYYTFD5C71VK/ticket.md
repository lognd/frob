+++
id = "01M5AXCG27BAJ1AYYTFD5C71VK"
title = "Reconcile declared adapter fidelity with measured corpus level (rust, markdown, python, typescript, html)"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-19T20:24:26Z"
updated = "2026-10-19T23:30:33Z"
scope = ["crates/gob-caps/**", "crates/gob-symbols/tests/**", "crates/gob-symbols/src/rust.rs", "crates/gob-symbols/src/python.rs", "crates/gob-symbols/src/markdown.rs", "crates/gob-symbols/src/html/mod.rs", "crates/gob-symbols/src/lib.rs", "docs/reference/languages.md", "docs/reference/fidelity.md"]

[[acceptance]]
text = "PINNED in measured.rs is empty and every_adapter_declares_the_fidelity_its_corpus_measures passes"
bound = true
+++

The measured-fidelity gate (crates/gob-symbols/tests/it/measured.rs) pins five divergences between the MATRIX declaration and what the corpus exhibits: rust F3 vs F4, markdown F4 vs F3, python F2 vs F3, typescript F2 vs F3, html F2 vs F0. Either correct the declaration in gob-caps MATRIX or extend the corpus, then delete the PINNED entries. Found while working ~QKJ78C2.
