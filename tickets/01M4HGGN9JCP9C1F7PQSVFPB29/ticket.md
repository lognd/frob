+++
id = "01M4HGGN9JCP9C1F7PQSVFPB29"
title = "GRL executor outcome gaps after ~BP7TEN3: NotApplicable per language from the capability matrix, the assumed:certainly@span conditional-fire cap (grl-spec 7.0.4), and dedicated UnresolvedReason variants for budget and partial"
type = "story"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-09T23:38:30Z"
updated = "2026-10-09T23:38:30Z"
scope = ["crates/gob-plan/src/exec/**", "crates/gob-rules/src/**", "changelog.d/**"]

[[acceptance]]
text = "Given a rule evaluated on a language whose capability matrix cell is not-applicable, when outcomes run, then the binding is NotApplicable, never clean or Unresolved"
bound = false

[[acceptance]]
text = "Given a fire that rests on a certainly() assumption, when outcomes run, then it is capped as conditional with reason assumed:certainly@span per grl-spec 7.0.4"
bound = false

[[acceptance]]
text = "Given a budget-truncated or partially parsed subject, when mapped to gob_rules::UnresolvedReason, then dedicated budget and partial variants are used, not Opaque codes"
bound = false
+++

Deferred by ~BP7TEN3's implementer (recorded as cut scope, not dropped).
