+++
id = "01M5AXCG27BAJ1AYYTFD5C71VK"
title = "Reconcile declared adapter fidelity with measured corpus level (rust, markdown, python, typescript, html)"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-19T20:24:26Z"
updated = "2026-10-19T23:19:06Z"
scope = ["crates/gob-caps/**", "crates/gob-symbols/tests/**"]

[[acceptance]]
text = "PINNED in measured.rs is empty and every_adapter_declares_the_fidelity_its_corpus_measures passes"
bound = false
+++

The measured-fidelity gate (crates/gob-symbols/tests/it/measured.rs) pins five divergences between the MATRIX declaration and what the corpus exhibits: rust F3 vs F4, markdown F4 vs F3, python F2 vs F3, typescript F2 vs F3, html F2 vs F0. Either correct the declaration in gob-caps MATRIX or extend the corpus, then delete the PINNED entries. Found while working ~QKJ78C2.
