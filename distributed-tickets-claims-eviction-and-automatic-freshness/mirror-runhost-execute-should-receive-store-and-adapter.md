+++
id = "01M5EBMAQGXNDFXXJMY3JDTJT5"
title = "mirror: RunHost::execute should receive store and adapter handles"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M5CVZND2H3YDDB67WZ7ANRQY"
reporter = "lognd"
created = "2026-10-21T04:31:06Z"
updated = "2026-10-21T07:35:25Z"
scope = ["crates/frob-mirror/src/host.rs", "crates/frob-mirror/src/run.rs", "crates/frob-mirror/src/progress.rs", "crates/frob-mirror/src/create.rs", "crates/frob-mirror/tests/host.rs", "changelog.d/01M5EBMAQGXNDFXXJMY3JDTJT5.changed.md"]

[[acceptance]]
text = "RunHost methods receive the driver store and adapter; MirrorHost holds no Shared handles and the host and run tests pass"
bound = true
+++

removes the Shared Rc RefCell aliasing workaround in host.rs; run() takes &mut store and &dyn TrackerAdapter while create_issue/recover/close_duplicates must mutate. found while working R2MH98S
