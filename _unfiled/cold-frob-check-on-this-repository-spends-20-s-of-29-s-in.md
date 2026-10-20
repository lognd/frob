+++
id = "01M42301J2JXZBNPKYTAKMV3C3"
title = "Cold frob check on this repository spends 20 s of 29 s in file-rules (release, 12-core host)"
type = "bug"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-03T23:53:38Z"
updated = "2026-10-03T23:53:38Z"
scope = ["crates/gob-check/src/**", "crates/frob-check/src/**"]
+++

found while working ~B6VY10G: the full_check bench in release measured cold stages graph 4.9 s, directives 0.9 s, file-rules 20.5 s (budgeted total 29 s; warm 1.2 s). The bench cold budget is set at 60 s as a regression guard; this ticket is to bring file-rules down so the budget can tighten.
