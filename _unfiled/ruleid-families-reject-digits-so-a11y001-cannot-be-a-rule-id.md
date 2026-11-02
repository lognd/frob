+++
id = "01M4TTRYY26E9ZFK26RPRGKSBX"
title = "RuleId families reject digits so A11Y001 cannot be a rule id"
type = "bug"
category = "done"
outcome = "wont-fix"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-13T14:30:58Z"
updated = "2026-11-02T11:31:01Z"
scope = ["crates/gob-rules/**"]
+++

found while working ~V4KM7K8: gob-rules RuleId requires 2-8 uppercase letters then 3 digits; crunk's A11Y family cannot parse, so eslint jsx-a11y maps to ACCESS001 for now. Allow digits in the family and switch the eslint map to A11Y001.
