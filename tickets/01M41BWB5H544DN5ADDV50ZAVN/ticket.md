+++
id = "01M41BWB5H544DN5ADDV50ZAVN"
title = "Changelog compile: a leading notice that sorts above the type groups of a release section"
type = "task"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-03T17:09:40Z"
updated = "2026-10-03T17:09:40Z"
scope = ["crates/frob-release/**", "docs/reference/changelog.md"]
+++

found while working ~2FCV344: acceptance 'the v2 notice leads the 0.532.0 section' cannot be met with fragments alone. A section is ordered product, type (added first), then fragment ULID, and a fragment named for another ticket (for example the epic, whose ULID sorts first) is refused by SCOPE001. Needs a lead-notice mechanism, for example a changelog.d/_lead.md file or a [release] notice knob, rendered above the product headings and covered by the section hash.
