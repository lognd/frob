+++
id = "01M6QWS4R90ZNJV6ZSZA5H50XT"
title = "TICK007: treat generated-page-only replay drift as Unresolved"
type = "bug"
category = "done"
outcome = "done"
priority = "high"
points = 1
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-11-06T07:39:42Z"
updated = "2026-11-06T07:49:38Z"
labels = ["no-story"]
scope = ["crates/frob-ledger/src/replay.rs", "crates/frob-ledger/src/reindex.rs"]

[[acceptance]]
text = "given a reindex commit whose replay differs only in generated pages, when TICK007 runs, then it reports Unresolved generator-drift, not Error"
bound = true
+++

no-story: ledger gate fix. Reindex commit 4e70c7bf81b0 differs from a replay only in GLOSSARY.md because generators changed under one version string; that is not a hand edit, so report Unresolved generator-drift instead of Error.
