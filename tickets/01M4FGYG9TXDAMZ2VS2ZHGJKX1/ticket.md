+++
id = "01M4FGYG9TXDAMZ2VS2ZHGJKX1"
title = "Kernel rules: label closure, clearance, boundary and rate findings"
type = "story"
category = "todo"
priority = "high"
points = 5
parent = "01M4FGWBHH3K9F2PPFYRGQ353T"
reporter = "lognd"
created = "2026-10-09T05:07:35Z"
updated = "2026-10-09T05:08:15Z"
idempotency_key = "logand-gaps-K1"
labels = ["adoption:logand-app", "grimble"]
scope = ["crates/grimble*/**", "crates/gob-*/**", "changelog.d/**"]

[[links]]
kind = "relates"
target = "01M3Z714MQBXMW4PJVRQNDWNDM"

[[acceptance]]
text = "Given flow f2 labelled Secret into a node with clearance Public, when grimble check runs, then a label-closure finding names f2"
bound = false

[[acceptance]]
text = "Given flow f1 from a foreign source into a trusted node with no endorsing boundary and no rate, when grimble check runs, then a finding names f1"
bound = false

[[acceptance]]
text = "Given the same flows with a boundary and a rate declared, when grimble check runs, then no finding"
bound = false
+++

Repro 06-label-closure-not-checked (~/projects/frob-v2-repros/logand-grimble-20261009/06-label-closure-not-checked): grimble-model.md section 3 kernel; no kernel rule is registered (rules are DSL, MDL, PARSE, SYS001/2/4 only). Relates ~QNDWNDM (G16); this is the flow-side half, claim verdicts are the sibling ticket.
