+++
id = "01M40FXV4AB47ASH79KJNF3JFH"
title = "usage error for missing required arguments lists none of them"
type = "bug"
category = "in-progress"
priority = "medium"
parent = "01M4065Y4N6DQG30TRSP2QNP8T"
reporter = "lognd"
created = "2026-10-03T09:01:09Z"
updated = "2026-10-03T10:08:19Z"
idempotency_key = "m2-rel-e2e-usage-lists-missing-args"
labels = ["milestone:2", "area:release", "release:0.532.0"]
scope = ["crates/gob-cli/src/cli.rs", "crates/gob-cli/tests/usage_missing_args.rs", "crates/frob/tests/e2e_init_loop.rs"]

[[acceptance]]
text = "Given frob ticket evidence add ~X --accepts 1, when it runs, then error.message names --provider and --ref and a usage line in remedy"
bound = true
+++

found while working ~7R0EMJ4. Exact failure: frob --json ticket evidence add ~X --accepts 1 exits 2 with E-USAGE message 'the following required arguments were not provided:' and nothing after it (clap lists them on the following lines, which the first-line extraction drops); remedy null. Bound by crates/frob/tests/e2e_init_loop.rs usage_error_names_the_missing_arguments (expected-to-fail; drop should_panic when fixed).
