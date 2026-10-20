+++
id = "01M48QZYWAMKC7MXHQ6AYNV7BN"
title = "Rule authoring: one rule, two files, compile errors first (D107)"
type = "epic"
category = "todo"
priority = "high"
reporter = "lognd"
created = "2026-10-06T13:56:02Z"
updated = "2026-10-06T14:50:24Z"

[[acceptance]]
text = "every child closed or dropped with a reason"
bound = false

[[acceptance]]
text = "a new rule in an existing crate is two hand-written files and nothing else"
bound = false
+++

Owner requirement: adding a universal or language-specific rule must be simple and impossible to get wrong, compile errors over runtime errors, and one rule's information side by side. Design: docs/design/rule-authoring.md (D107); detail and the failure table: notes/research/rule-authoring.md section 4.
