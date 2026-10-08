+++
id = "01M4DYPEJYZSKH9VDD1AJKH9PM"
title = "Land gate covers CI-only steps: rustdoc -D warnings and the generated-files check run as tool stages or required evidence"
type = "task"
category = "todo"
priority = "high"
points = 3
parent = "01M4CTDVKQVPSY0SF4XTNT2Q1E"
reporter = "lognd"
created = "2026-10-08T14:29:23Z"
updated = "2026-10-08T14:29:23Z"
scope = ["changelog.d/**", "crates/frob-check/**", "crates/frob-land/**", "crates/gob-dev/**", "frob.toml"]

[[acceptance]]
text = "Given a ticket whose public docs link a private item, when frob check --ticket or land runs, then it fails naming the rustdoc error"
bound = false
+++

2026-10-08: ~8JGRZY3 landed with rustdoc private-link errors; frob check did not run the docs step, CI went red, every land was blocked until hotfix ~8M993C2.
