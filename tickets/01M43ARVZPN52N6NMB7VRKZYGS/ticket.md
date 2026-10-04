+++
id = "01M43ARVZPN52N6NMB7VRKZYGS"
title = "crunk-tailwind: default-theme tables and utility candidate parser"
type = "story"
category = "in-progress"
priority = "medium"
points = 5
parent = "01M43ANVJYA7GHN0Y8GX0SN72M"
reporter = "lognd"
created = "2026-10-04T11:28:46Z"
updated = "2026-10-04T11:54:06Z"
idempotency_key = "crunk-plan-tw"
labels = ["area:crunk"]
scope = ["crates/crunk-tailwind/**", "Cargo.lock"]

[[acceptance]]
text = "Given the class `md:hover:-mt-[13px]/50`, when parsed, then variants, negation, utility, arbitrary value and alpha are separate fields"
bound = true

[[acceptance]]
text = "Given each v3 and v4 default key table, when compared to the Python tw_defaults, then the key sets are equal"
bound = true

[[acceptance]]
text = "Given a computed className fragment, when parsed, then only static fragments yield candidates and the rest is reported as dynamic"
bound = true
+++

Port tailwind default-key tables (v3 and v4, tw_defaults.py) and replace the regex utility-name parsing of rules/_tailwind.py with a real candidate parser (variants, important, arbitrary values, alpha suffix, negative values); this is crunk v1 queued T-0294. Pure crate, no process spawning (the node bridge is a later ticket). Boundaries 2.4 (crunk_tailwind). Port tests/unit/test_rules_tailwind.py parsing cases and tests/fixtures/tailwind_v4.
