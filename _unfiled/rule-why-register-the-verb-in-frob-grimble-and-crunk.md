+++
id = "01M4PT1A52YR3QV6PYSGNC7N38"
title = "rule why: register the verb in frob, grimble and crunk"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-12T01:01:06Z"
updated = "2026-10-24T05:34:34Z"
scope = ["crates/frob/src/rule_cmd.rs", "crates/grimble/src/rule_cmd.rs", "crates/gob-dev/profile.toml", "docs/design/grl-spec.md", "crates/frob/src/product.rs", "crates/grimble/src/lib.rs", "crates/frob/tests/**", "crates/grimble/tests/**", "docs/reference/**", "docs/schemas/**", "docs/guide/**"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7H8FPEAY1X1WVW1PNXXN"

[[acceptance]]
text = "Given a rule file and FILE:LINE, when 'rule why ID FILE:LINE' runs in frob and grimble, then it prints the why trace text and exits 0"
bound = false
+++

Library gob_plan::verbs::why::why_source exists (ticket W1PNXXN). Wire thin 'rule why ID FILE:LINE' commands in every product (see rule_cmd.rs), add the scenario to crates/gob-dev/profile.toml, regenerate generated pages. Also: check why the 'inside test' kind never matched a TS vitest test() callback in the executor.
