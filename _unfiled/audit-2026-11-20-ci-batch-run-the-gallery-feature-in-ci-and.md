+++
id = "01M7X35T96D3GNAQS78A758TVD"
title = "Audit 2026-11-20 CI batch: run the gallery feature in CI and fix vacuous or mis-bound tests"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-20T18:23:22Z"
updated = "2026-11-20T22:01:55Z"
labels = ["no-story"]
scope = [".github/**", "crates/*/tests/**"]

[[acceptance]]
text = "Given CI, when nextest runs, then crunk's gallery-gated tests (gallery.rs, render_browser.rs, render_solve.rs) are built and run on at least the Linux leg"
bound = true

[[acceptance]]
text = "Given the vacuous tests, when their setup fails, then they fail: redact.rs the_repository_contains_neither_rule_nor_term asserts exit codes, gallery.rs GalleryCheck binding points at a test that exercises it, and the fixed-port reuse is replaced by reading the bound port"
bound = false
+++

no-story: internal CI and test-quality hardening from the 2026-11-20 audit; no user-visible behavior change. Audit finding: crunk default=[] and ci.yml:358 / gob-dev ci.rs:311-326 never enable gallery, so 19 tests never run in CI. Others: crates/frob/tests/it/redact.rs:220, crates/crunk/tests/it/gallery.rs:16-18 and :184, crates/crunk/tests/it/rename.rs:186 silent pass under root and on Windows.
