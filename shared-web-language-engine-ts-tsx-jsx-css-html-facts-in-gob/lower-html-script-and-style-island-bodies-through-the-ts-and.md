+++
id = "01M48E13W9MYK85YTCWSSRS50S"
title = "Lower HTML script and style island bodies through the TS and CSS adapters (nested-fold seam)"
type = "story"
category = "todo"
priority = "medium"
parent = "01M47QJ3CHWZBZ6R3QHN4R2XN5"
reporter = "lognd"
created = "2026-10-06T11:01:54Z"
updated = "2026-10-06T11:01:54Z"
scope = ["crates/gob-symbols/**"]

[[acceptance]]
text = "a CSS rule inside an HTML style element answers the style queries with spans in the HTML file"
bound = false

[[acceptance]]
text = "a function call inside an HTML script element appears in the call graph"
bound = false
+++

Deferred by ~EEYTQ0J: <script> and <style> bodies are region islands tagged js/ts/json/data/css but are not lowered, so a CSS rule in a <style> block is no style.declaration and script calls are not in the graph. Each adapter builds its own per-file term; add a seam that folds a nested body into the host builder at a byte offset, reuse it for HTML islands and for css-tagged template literals in TSX (language-engines.md 2-3, D96).
