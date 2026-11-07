+++
id = "01M6VS2WG7D9FE1WP124SGK80K"
title = "Move AGENT_MARKERS below gob-trust so gob-trust stops depending on gob-cli"
type = "bug"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-11-07T19:52:04Z"
updated = "2026-11-07T19:52:04Z"
scope = ["crates/gob-trust/**", "crates/gob-cli/**"]
+++

found while working ~GYNK2NK: gob-trust (layer 3) imports gob_cli::AGENT_MARKERS (layer 7). Move the constant to a lower crate and drop the ALLOWED row in crates/gob-dev/tests/layering.rs.
