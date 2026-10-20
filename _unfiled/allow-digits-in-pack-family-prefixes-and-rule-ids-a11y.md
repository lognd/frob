+++
id = "01M4ZYNRNH24WCD69FR7ZQ226N"
title = "Allow digits in pack family prefixes and rule ids (A11Y)"
type = "bug"
category = "done"
outcome = "done"
priority = "high"
points = 2
reporter = "lognd"
created = "2026-10-15T14:15:20Z"
updated = "2026-10-15T15:07:23Z"
scope = ["crates/gob-packs/src/validate.rs", "crates/gob-plan/src/grl/lexer.rs", "docs/design/grl-spec.md"]

[[acceptance]]
text = "Given a pack family A11Y and rule id A11Y101, when validated and lexed, then both are accepted, while lowercase, leading-digit and non-3-digit-suffix forms are rejected"
bound = true
+++

found while working ~X5W2SPP: pack.families requires 2+ capital letters A-Z (validate.rs family) and is_rule_id requires [A-Z]+[0-9]{3} (lexer.rs), so the crunk-web family A11Y and rule ids like A11Y101 are rejected (PACK005 / 'not a valid name or rule id'). Fix: allow digits after the first letter in family prefixes (e.g. [A-Z][A-Z0-9]+ ending in a letter or digit) and rule ids ([A-Z][A-Z0-9]*[0-9]{3}), keep crates/crunk-rules/src/family.rs consistent.
