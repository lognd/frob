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
updated = "2026-10-21T07:16:16Z"
scope = ["crates/frob-mirror/src/host.rs"]
+++

removes the Shared Rc RefCell aliasing workaround in host.rs; run() takes &mut store and &dyn TrackerAdapter while create_issue/recover/close_duplicates must mutate. found while working R2MH98S
