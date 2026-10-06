+++
id = "01M48TKSG9SCKND40YXK0FVJFM"
title = "GRL grammar ambiguities found by the printer's generator: leading where after an open binding, reaches..via list inside any {}"
type = "bug"
category = "todo"
priority = "medium"
parent = "01M3ZWPE0CNFWB4PTW3D05GDWP"
reporter = "lognd"
created = "2026-10-06T14:41:49Z"
updated = "2026-10-06T14:41:49Z"
scope = ["crates/gob-plan/**", "docs/design/grl-spec.md"]

[[acceptance]]
text = "a where clause after an unfiltered find parses as a clause, and a filter needs explicit syntax, in both the spec and the parser"
bound = false

[[acceptance]]
text = "reaches..via inside any {} parses each item separately"
bound = false

[[acceptance]]
text = "the printer's parenthesis workarounds are removed and the generator covers both shapes"
bound = false
+++

Found by ~NH92W1H's proptest generator: (1) a where at the start of a line is consumed as the filter of a still-open some/no binding, so a where clause directly after an unfiltered find/some/no cannot be expressed; (2) reaches X via a, b without within, followed by a comma inside any { }, swallows the next item as another verb. The printer parenthesises around both; fix the grammar (grl-spec.md section 5) so each source has one parse, document the rule, and remove the printer's workarounds.
