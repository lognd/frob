+++
id = "01M4D95B4W3XEMKKFG4B2ZBRER"
title = "Rule precision ledger: per-rule accept, waive, dismiss and fix counts and a not-useful rate; Warn by default needs measured precision"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 3
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-08T08:13:02Z"
updated = "2026-10-11T01:41:37Z"
scope = ["changelog.d/**", "crates/gob-rules/**", "crates/gob-check/**", "crates/frob-check/src/verb.rs", "crates/frob-check/tests/precision.rs", "docs/design/rules.md", "docs/schemas/envelope.json"]

[[acceptance]]
text = "Given exceptions recorded for a rule in a run, when the report builds its precision ledger, then the rule has its accepted and waived counts, open findings and a not-useful rate, and the rate is absent below the minimum sample size"
bound = true

[[acceptance]]
text = "Given a ledger where a rule's not-useful rate is above a ceiling with enough samples, when demotions are asked for, then that rule is returned with its numbers and the rules at or below the ceiling are not"
bound = true

[[acceptance]]
text = "Given exceptions in the tree, when frob check --json runs, then data.precision lists each rule with its counts and not-useful rate"
bound = true
+++

notes/research/lint-catalogue-2026-10-08.md 1.1 P and 4.2 N16; notes/research/creators-systems-2026-10-08.md 5.2 (Tricorder: tuning cut the not-useful rate from 80 to about 15 percent; deploy only low-false-positive checks); ~GR4ZPYH measured about 5 percent true positives for v1 web rules; notes/research/deslop-research-2026-10-08.md 4.8 verdict eval loop.
