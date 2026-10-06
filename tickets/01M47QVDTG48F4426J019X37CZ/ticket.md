+++
id = "01M47QVDTG48F4426J019X37CZ"
title = "cargo-deny, cargo-shear, typos and MSRV steps in cargo dev ci"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 3
parent = "01M47QTS14TAZQ67NN2M9NHDJP"
reporter = "lognd"
created = "2026-10-06T04:34:19Z"
updated = "2026-10-06T10:55:36Z"
scope = ["crates/gob-dev/**", ".github/workflows/ci.yml", "deny.toml", "typos.toml", "frob.toml", "Cargo.toml"]

[[acceptance]]
text = "the four steps run in cargo dev ci and in ci.yml through it"
bound = true

[[acceptance]]
text = "each passes on experimental"
bound = true

[[acceptance]]
text = "every allow entry carries a reason"
bound = true
+++

build-test-ci.md sections 4 and 6. Four steps, each tool version pinned in frob.toml like zizmor: deny (advisories, licenses, bans with a deny.toml), shear (unused dependencies), typos (with a typos.toml for domain words), msrv (cargo check at the workspace rust-version). Fix what they find or allow it with a reason.
