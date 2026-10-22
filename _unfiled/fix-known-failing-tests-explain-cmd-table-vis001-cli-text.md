+++
id = "01M5H5WSR0H3YJHAPAMM7F4X3Q"
title = "Fix known failing tests: explain_cmd table VIS001, cli text_format, wiring sibling_verbs_print_schemas, web_conformance SYS013, reindex budget"
type = "bug"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-22T06:48:36Z"
updated = "2026-10-22T07:15:21Z"
scope = ["crates/frob/**", "crates/frob-ledger/**"]

[[acceptance]]
text = "Given a clean checkout, when the five named tests run, then they pass"
bound = false
+++

Failing: explain_cmd::tests::the_table_covers_every_generated_page_of_the_product; cli::text_format_goes_to_stdout_and_errors_to_stderr (crates/frob/tests/it/cli.rs:239); wiring::sibling_verbs_print_schemas; web_conformance SYS013; profile command budget for ticket reindex warm (2025ms vs 1000ms). Re-check first: some may be stale-binary fallout.
