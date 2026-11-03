+++
id = "01M64A0BAMDV8K8H2WGMCKJGJZ"
title = "gob-cli depends on frob-present, failing layering/boundary tests (SYS013)"
type = "bug"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-29T17:06:01Z"
updated = "2026-11-03T05:56:44Z"
scope = ["crates/gob-cli/**"]
+++

Found while working ~394FZ5T, pre-existing: gob-dev::layering, grimble::boundary and crunk::boundary fail because gob-cli depends on frob-present (crosses products).
