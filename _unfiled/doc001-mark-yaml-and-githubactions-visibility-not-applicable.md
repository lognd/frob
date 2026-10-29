+++
id = "01M62EB4V7ZG8MCFQ4H7HTED6Y"
title = "DOC001: mark YAML and GithubActions visibility not-applicable in the capability matrix"
type = "bug"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-28T23:43:20Z"
updated = "2026-10-29T00:40:15Z"
scope = ["crates/gob-caps/**", "crates/gob-check/**", "docs/reference/languages.md"]

[[acceptance]]
text = "Given a YAML or GithubActions file, when DOC001 runs, then no capability-gap visibility finding is reported (matrix cell is NotApplicable)"
bound = true
+++

Found while working ~2WNFCDP. DOC001 reports 'capability gap: visibility' as unresolved for every .yml under .github (13 files) because Lang::Yaml/GithubActions have a Gap visibility cell in crates/gob-caps/src/matrix.rs; YAML declares no public items, so the cell should be NotApplicable (like Css/Html). frob:accept cannot suppress an unresolved.
