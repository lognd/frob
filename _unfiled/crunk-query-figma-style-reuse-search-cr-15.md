+++
id = "01M1QDTV17G8YGQ22PG8T0QJ56"
title = "crunk query: Figma-style reuse search (CR-15)"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
reporter = "human"
created = "2026-09-05T00:00:00Z"
updated = "2026-10-27T00:53:31Z"
aliases = ["crunk:T-0039"]
labels = ["component:crunk", "source:crunk", "imported:crunk"]
scope = ["src/crunk/query/**", "src/crunk/report/query_out.py", "src/crunk/report/__init__.py", "src/crunk/app/**", "src/crunk/__main__.py", "tests/unit/test_query.py", "tests/unit/test_report_query.py", "tests/unit/test_app.py", "tests/unit/test_main.py", "tests/integration/test_int_10_query.py", "tests/system/test_e2e_16_query.py", "docs/commands/query.md", "docs/design/subsystems/query.md", "docs/design/subsystems/shell.md", "README.md", "docs/index.md", "docs/commands/check.md", "docs/commands/fix.md", "docs/commands/init.md", "docs/commands/map.md", "docs/commands/tokens.md"]

[[links]]
kind = "blocked-by"
target = "01M1QDTV11YBN4ZWJ0J4H8A2Q4"

[[links]]
kind = "blocked-by"
target = "01M1QDTV15N0TWQVWNK2GVF83C"

[[acceptance]]
text = "given the reuse fixture (a card component, a planted near-duplicate pair, an unused token), when each query subcommand runs, then find ranks card first with use counts, dupes reports exactly the planted pair, unused exactly the planted token, and all --json variants parse (E2E-16, INT-10)"
bound = false
+++

Per r4 query.md (the contract is complete there): query/models.py answer union + QueryError, query/engine.py find/component_card/dupes/unused/uses/nearest_colors with the documented ranking, similarity, and tie-break semantics; report/query_out.py render_query/render_query_json; shell dispatch (query violations filters the ordinary check pipeline in the shell; unused receives token_names from the shell like rules does). CLI: crunk query subparsers + --json; README command table + docs/commands/query.md. UT-QRY-01..06, UT-REP-06, INT-10, E2E-16.
