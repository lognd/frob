+++
id = "01M4FGZ39WXWBRDRHW2ADSY7K8"
title = "vmodel ref: resolve table-row id anchors and slugs, and report a malformed ref"
type = "bug"
category = "todo"
priority = "medium"
points = 3
parent = "01M4FGWBHH3K9F2PPFYRGQ353T"
reporter = "lognd"
created = "2026-10-09T05:07:55Z"
updated = "2026-10-09T05:08:22Z"
idempotency_key = "logand-gaps-V2"
labels = ["adoption:logand-app", "grimble"]
scope = ["crates/grimble-bind/**", "crates/grimble-model/**", "changelog.d/**"]

[[links]]
kind = "relates"
target = "01M4FGZ22EX779T6RNS4FKJ689"

[[acceptance]]
text = "Given ref docs/r.md:COMP-0101, when grimble check runs, then a finding names the malformed symref and suggests the # spelling"
bound = false

[[acceptance]]
text = "Given ref docs/spec/L2.md#spec-060 where spec-060 is a table row id, when grimble check runs, then it binds"
bound = false

[[acceptance]]
text = "Given a heading with a code span, when referenced by its GitHub slug, then it binds"
bound = false
+++

Repros 12 (~/projects/frob-v2-repros/logand-grimble-20261009/12-vmodel-ref-table-row-anchor) and 15-vmodel-ref-single-colon-silent (~/projects/frob-v2-repros/logand-grimble-20261009/15-vmodel-ref-single-colon-silent). 12 follows the anchor decision of the vmodel docs ticket. 15 is independent: ref docs/r.md:COMP-0101 (v1 spelling) produces no finding and no binding row, so an unresolvable ref silently disappears.
