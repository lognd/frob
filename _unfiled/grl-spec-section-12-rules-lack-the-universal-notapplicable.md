+++
id = "01M4DPRS9DZ8NGVP9MBGV4D8CQ"
title = "grl-spec section 12 rules lack the universal notapplicable or unresolved example that GRL011 now requires"
type = "bug"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-08T12:10:51Z"
updated = "2026-10-08T12:10:51Z"
scope = ["crates/gob-plan/src/grl/parse/tests/fixtures/**", "docs/design/grl-spec.md"]
+++

found while working ~ZKM5W7Y. The fixture rules (CAP001 and others with lang *) omit the third example; tests/check_names.rs the_fixture_rules_of_the_spec_check_clean filters that one GRL011 message until they are completed.
