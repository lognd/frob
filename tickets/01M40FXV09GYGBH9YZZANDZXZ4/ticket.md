+++
id = "01M40FXV09GYGBH9YZZANDZXZ4"
title = "frob check without frob.toml runs the rules instead of teaching 'run frob init' (diagnostics.md section 5)"
type = "bug"
category = "in-progress"
priority = "medium"
parent = "01M4065Y4N6DQG30TRSP2QNP8T"
reporter = "lognd"
created = "2026-10-03T09:01:09Z"
updated = "2026-10-03T09:55:56Z"
idempotency_key = "m2-rel-e2e-check-before-init-teaches"
labels = ["milestone:2", "area:release", "release:0.532.0"]
scope = ["crates/frob/src/lib.rs", "crates/frob/tests/check_verb.rs", "crates/gob-cli/src/cli.rs", "crates/frob/src/first_run.rs", "crates/frob/tests/e2e_init_loop.rs", "crates/frob/tests/first_run.rs"]

[[acceptance]]
text = "Given a git repository with no frob.toml, when frob check runs, then it exits non-zero with one diagnostic that names frob init and what it writes, and no rule findings"
bound = true
+++

found while working ~7R0EMJ4. Exact failure: in a repository with a Cargo crate and no frob.toml, frob --json check exits 0 with ok true and 7 unresolved DRIFT001..TODO001 findings about an opaque .gitignore; nothing says to run frob init. Bound by crates/frob/tests/e2e_init_loop.rs check_before_init_says_to_run_init (expected-to-fail; drop should_panic when fixed). Overlaps ~RPWPGD2 (first-run teaching); this ticket is the release-0.532.0 slice.
