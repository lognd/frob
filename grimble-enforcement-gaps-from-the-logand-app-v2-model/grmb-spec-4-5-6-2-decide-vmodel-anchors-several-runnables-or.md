+++
id = "01M4FGZ22EX779T6RNS4FKJ689"
title = "grmb-spec 4.5/6.2: decide vmodel anchors, several runnables or manual per test, and runner-id mapping"
type = "docs"
category = "todo"
priority = "medium"
points = 3
parent = "01M4FGWBHH3K9F2PPFYRGQ353T"
reporter = "lognd"
created = "2026-10-09T05:07:53Z"
updated = "2026-10-09T05:07:53Z"
idempotency_key = "logand-gaps-V1"
labels = ["adoption:logand-app", "grimble"]
scope = ["docs/design/grmb-spec.md", "docs/design/binding.md", "changelog.d/**"]

[[acceptance]]
text = "Given the decision, when grmb-spec 4.5 is read, then it defines table-row id anchors, explicit {#id} anchors and GitHub slug rules for code spans"
bound = false

[[acceptance]]
text = "Given a test backed by several runner ids and a manual test, when the spec is read, then each has a stated form and finding"
bound = false

[[acceptance]]
text = "Given vitest titles and cargo paths, when the spec is read, then a table maps runner ids to selectors and states how test units are recognised outside tests/"
bound = false
+++

Repros 12-vmodel-ref-table-row-anchor (~/projects/frob-v2-repros/logand-grimble-20261009/12-vmodel-ref-table-row-anchor), 13-vmodel-runnable-one-or-manual (~/projects/frob-v2-repros/logand-grimble-20261009/13-vmodel-runnable-one-or-manual) and 14-vmodel-ts-rust-runnable-names (~/projects/frob-v2-repros/logand-grimble-20261009/14-vmodel-ts-rust-runnable-names). Design gaps: spec row ids in markdown tables cannot be anchors and heading slugs with code spans or ampersands do not resolve; a test with several runner ids or a manual test has no form (SYS003/MDL014); vitest titles and cargo paths have no derivable selector and tests are recognised only under a tests directory. Decide each and write the answers in grmb-spec 4.5 and 6.2 and binding.md B9.
