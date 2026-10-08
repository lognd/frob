+++
id = "01M4D92HMPWHFY5WGGY3KGFTNE"
title = "typos JSON parser mapped to SPELL001 (Advisory), honouring typos.toml"
type = "task"
category = "todo"
priority = "medium"
points = 2
parent = "01M4D8X558Q07HCMEBP224NQP4"
reporter = "lognd"
created = "2026-10-08T08:11:30Z"
updated = "2026-10-08T08:11:30Z"
scope = ["changelog.d/**", "crates/gob-check/**", "crates/frob/**"]

[[acceptance]]
text = "Given typos --format json output, when parsed, then each typo is a SPELL001 finding with the correction in the remedy"
bound = false

[[acceptance]]
text = "Given an allowlisted word in typos.toml, when checked, then no finding"
bound = false
+++

notes/research/lint-catalogue-2026-10-08.md row K11 (4.2 N06): notes/research/mining-report-2026-10-08.md C09 1.9 percent of human review comments, F-DOC-TYPO 9.2 percent of fix commits; typos already runs pass/fail in cargo dev ci (~19X37CZ).
