+++
id = "01M5XBTMCCFSS2X4J6BPGYE0EB"
title = "Guide gitattributes template lacks merge-driver patterns and LF pin, so reindex fights branch init"
type = "bug"
category = "in-progress"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-27T00:23:09Z"
updated = "2026-11-15T15:07:35Z"
scope = ["crates/frob-ledger/templates/**", "crates/frob-ledger/src/gen/guide.rs"]

[[acceptance]]
text = "The guide .gitattributes embeds the branch merge-driver patterns and LF pin"
bound = true
+++

found while working ~CHJYNT6: the guide generator .gitattributes differs from branch_gitattributes/pin_eol, so the first reindex after migration rewrites it.
