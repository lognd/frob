+++
id = "01M4GKBEBGBTA03VFB90SDR858"
title = "Evidence test node ids are pytest-rootdir-relative instead of repository-relative; test-only tickets need an explicit changelog exemption path"
type = "bug"
category = "in-progress"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-09T15:08:51Z"
updated = "2026-10-10T20:47:51Z"
labels = ["adoption:logand-app"]
scope = ["crates/frob-evidence/**", "crates/frob-tests/**", "crates/frob-release/**", "changelog.d/**"]

[[acceptance]]
text = "Given a pytest rootdir below the repository root, when evidence is recorded, then node ids are repository-relative"
bound = false

[[acceptance]]
text = "Given a ticket of type test or chore whose diff touches only tests, when it lands, then the changelog fragment guard is satisfied without --no-changelog, per a [pm.done] knob"
bound = false
+++

logand.app-v2 F-551.
