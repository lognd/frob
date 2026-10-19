+++
id = "01M5ANA1DJ6V3MDF3NJZXAS6JW"
title = "Wire frob explain: register the Explain verb (needs lib.rs/product.rs, held by KNMAEDB)"
type = "task"
category = "in-progress"
priority = "medium"
points = 1
reporter = "lognd"
created = "2026-10-19T18:03:17Z"
updated = "2026-10-19T18:36:28Z"
scope = ["crates/frob/src/lib.rs", "crates/frob/src/product.rs", "crates/frob/tests/it/main.rs", "docs/reference/cli/frob.md"]
+++

found while working ~992NX3A. crates/frob/src/explain_cmd.rs and crates/frob/tests/it/explain.rs exist but are unwired because lib.rs/product.rs were leased by KNMAEDB. Do: add 'pub mod explain_cmd;' to lib.rs; 'let cli = cli.register::<crate::explain_cmd::Explain>();' before frob_lease::register(cli) in product.rs; 'mod explain;' in tests/it/main.rs; run gob-dev gen all and keep only docs/reference/cli/frob.md. Then run cargo test -p frob-cli explain. first_run.rs already lists explain as needing no frob.toml.
