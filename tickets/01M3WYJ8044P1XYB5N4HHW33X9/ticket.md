+++
id = "01M3WYJ8044P1XYB5N4HHW33X9"
title = "gob-text: spans, line index, source text"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 3
parent = "01M3WYJ802PGVRR55XCM9C3KV9"
reporter = "agent"
created = "2026-10-02T00:00:00Z"
updated = "2026-10-02T00:00:03Z"
aliases = ["T-0004"]
labels = ["milestone:2.0.0", "component:gob-text"]
scope = ["crates/gob-text/**"]

[[links]]
kind = "blocked-by"
target = "01M3WYJ803MT624EZ2NSPNY907"

[[acceptance]]
text = "Given any UTF-8 text and a byte offset inside it, when converted to line/column and back, then the original offset is returned"
bound = false

[[acceptance]]
text = "Given a span on a line, when rendered, then the snippet shows the line and a caret under the span"
bound = false
+++

Implement crates/gob-text per architecture.md section 1 and code-model.md section 2 (spans for every finding). Types: TextSize/TextRange (newtype over u32, like ruff_text_size; evaluate depending on the ruff_text_size crate from crates.io first and prefer it if its API fits, documenting the choice), LineIndex (byte offset to 1-based line/column, UTF-8 aware, UTF-16 column helper for LSP later), SourceText (Arc<str> plus LineIndex, lazily built), Span { file: FileId, range }. FileId is an interned newtype owned here. Include a snippet renderer helper that returns the line of a span with a caret (used by gob-diagnostics text output). Property tests with proptest for offset round-trips. Rustdoc on everything with examples that compile as doctests.
