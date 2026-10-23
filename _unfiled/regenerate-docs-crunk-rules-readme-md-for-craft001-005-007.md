+++
id = "01M5KM102PMKFXQE3NB68Z8PDV"
title = "Regenerate docs/crunk/rules/README.md for CRAFT001-005,007,009,011,012"
type = "docs"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-23T05:34:02Z"
updated = "2026-10-23T05:34:02Z"
scope = ["docs/crunk/rules/README.md"]
+++

Found while working ~2C2A8A0: the lease on docs/crunk/** is held by CXX0FRT, so the registry rows could not be committed. Run gob-dev gen all once 2C2A8A0 merges; the_committed_registry_page_is_fresh in crates/crunk-check/tests/waive001.rs fails until then.
