+++
id = "01M5XBTMCCFSS2X4J6BPGYE0EB"
title = "Guide gitattributes template lacks merge-driver patterns and LF pin, so reindex fights branch init"
type = "bug"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-27T00:23:09Z"
updated = "2026-10-27T00:23:09Z"
scope = ["crates/frob-ledger/templates/**", "crates/frob-ledger/src/gen/guide.rs"]
+++

found while working ~CHJYNT6: the guide generator .gitattributes differs from branch_gitattributes/pin_eol, so the first reindex after migration rewrites it.
