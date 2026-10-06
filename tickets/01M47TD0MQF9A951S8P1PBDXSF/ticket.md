+++
id = "01M47TD0MQF9A951S8P1PBDXSF"
title = 'GRL parser accepts the dotted field form in kind patterns, element(.tag = "img"), as grl-spec.md writes it'
type = "bug"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-06T05:18:53Z"
updated = "2026-10-06T05:18:53Z"
scope = ["crates/gob-plan/**", "docs/design/grl-spec.md"]

[[acceptance]]
text = "every GRL example in docs/design/grl-spec.md parses in a test"
bound = false

[[acceptance]]
text = "the printer emits one canonical field form and the spec states it"
bound = false
+++

Found by ~4N35GSV: grl-spec.md section 6 writes fields with a leading dot (element(.tag = "img"), key(.path = ...)) but the GRL parser in crates/gob-plan only accepts the bare form (element(tag = "img")). Either the parser accepts both with one canonical printed form, or the spec changes to the bare form everywhere; pick one, record it, and make the examples in docs/design/grl-spec.md and the catalog page parse in a test.
