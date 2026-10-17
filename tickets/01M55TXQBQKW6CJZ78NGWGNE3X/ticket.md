+++
id = "01M55TXQBQKW6CJZ78NGWGNE3X"
title = "gob-rules Out: range-capable emission so COV001 and TODO002 can migrate to the two-file shape"
type = "bug"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-17T21:05:13Z"
updated = "2026-10-17T21:05:13Z"
scope = ["crates/gob-rules/**"]
+++

found while working ~MXXGNZ3: Emitted/Out keep only a start offset, so the span end is lost; relay is forbidden with must_measure. Add end to Emitted plus Out::fire_range/unresolved_range, then migrate COV001 and TODO002.
