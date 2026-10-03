+++
id = "01M41BWB5H544DN5ADDV50ZAVN"
title = "Changelog compile: a leading notice that sorts above the type groups of a release section"
type = "task"
category = "in-progress"
priority = "medium"
parent = "01M4065Y4N6DQG30TRSP2QNP8T"
reporter = "lognd"
created = "2026-10-03T17:09:40Z"
updated = "2026-10-03T17:14:29Z"
scope = ["crates/frob-release/**", "docs/reference/changelog.md"]

[[acceptance]]
text = "Given the changelog compile, when run, then the v2 notice leads the 0.532.0 section"
bound = false

[[acceptance]]
text = "Given a fragment marked as a lead notice, when release changelog compiles a section, then it appears first, above the type groups, and at most one lead notice per section is accepted"
bound = false
+++

found while working ~2FCV344: acceptance 'the v2 notice leads the 0.532.0 section' cannot be met with fragments alone. A section is ordered product, type (added first), then fragment ULID, and a fragment named for another ticket (for example the epic, whose ULID sorts first) is refused by SCOPE001. Needs a lead-notice mechanism, for example a changelog.d/_lead.md file or a [release] notice knob, rendered above the product headings and covered by the section hash.
