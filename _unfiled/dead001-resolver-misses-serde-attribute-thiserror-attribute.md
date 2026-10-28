+++
id = "01M61G1Y62DQKF195X9JWEYWT8"
title = "DEAD001 resolver misses serde attribute, thiserror attribute and fn-value edges; generated rules_index_is_fresh test flagged"
type = "bug"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-28T14:54:01Z"
updated = "2026-10-28T14:54:01Z"
scope = ["crates/gob-rules/src/indexgen.rs", "crates/frob-code/**"]
+++

Found while working ~RFX8QWR. DEAD001 reports as Unresolved: serde with/default attribute targets (frob-ledger event.rs rel_path, redact.rs yes), a thiserror attribute method call (model.rs PointScale::describe), and functions passed as values (index.rs summary_row, ops.rs is_empty_list, redact.rs Rule::hit). Also the generated mod freshness test rules_index_is_fresh emitted by crates/gob-rules/src/indexgen.rs:290 is flagged DEAD001 in about 15 crates; the generator should emit a marker the rule honors. Fix the resolver or generator, then drop the frob:defer directives that cite this ticket.
