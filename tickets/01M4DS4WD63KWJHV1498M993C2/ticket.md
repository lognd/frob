+++
id = "01M4DS4WD63KWJHV1498M993C2"
title = "crunk-ingest: rustdoc -D warnings fails on jsx module docs linking private items (CI red)"
type = "bug"
category = "todo"
priority = "critical"
class = "expedite"
points = 1
parent = "01M43ANVJYA7GHN0Y8GX0SN72M"
reporter = "lognd"
created = "2026-10-08T12:52:24Z"
updated = "2026-10-08T12:52:24Z"
scope = ["crates/crunk-ingest/**", "changelog.d/**"]

[[acceptance]]
text = "Given cargo dev ci --step docs, when run, then it passes"
bound = false
+++

The docs step (RUSTDOCFLAGS -D warnings) fails: public docs of the jsx module link to private modules style, classes and ingest (rustdoc::private_intra_doc_links). Replace with plain code spans.
