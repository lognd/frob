+++
id = "01M5DBVTCDGK4Z096B1ZXVW75J"
title = "Resume a claim on another clone as the same actor"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-20T19:15:57Z"
updated = "2026-11-09T23:31:34Z"
scope = ["crates/frob-worktree/**", "crates/frob-ledger/src/event.rs", "crates/frob-ledger/src/claim_hold.rs", "docs/design/frob/distributed-tickets.md", "changelog.d/01KZ7KGKHYQ1QZ0BHKB49P22KK.changed.md", "changelog.d/01M1QDTYR2FFF5HYHVZP2W1WMP.fixed.md", "changelog.d/01M1QDTYRJ3P3GT8828GCNECVB.added.md", "changelog.d/01M1T07NW78MGWRF7HZQMPSRAV.security.md", "changelog.d/01M1T07NWAFVRT2V4RAPVJ9SQM.added.md", "changelog.d/01M1T07NX1SZYZBZYYW821FN00.added.md", "changelog.d/01M1T07NY615PQ6RAEB4CESXMT.security.md", "changelog.d/01M2VFD1ZAS7PZERWYPQDMB8GH.added.md", "changelog.d/01M2VFD1ZBJP6X2ACJ4KCF29W6.added.md", "changelog.d/01M2VFD1ZDWWNTW1FFGKHCKTS3.added.md", "changelog.d/01M3AXSDBMG2ZAEHTQ6JHA8CYK.fixed.md", "changelog.d/01M3DG64C705481E6V5X4W9S9S.fixed.md", "changelog.d/01M3DG64CFWRYVDS3DGW91G8EK.added.md", "changelog.d/01M3DG64CNAZ8K50HQ046VKHER.added.md", "changelog.d/01M3DG64ECQN5RFA286F6YXYRZ.added.md", "changelog.d/01M3Z713C4RW0T6XK1ZB7VH1B4.changed.md", "changelog.d/01M3Z7141TW2H3HXJRK1QBHP7T.added.md", "changelog.d/01M3Z714EEST9EGEHWWV56RXG4.added.md", "changelog.d/01M3Z714HJ6E02VGXH271BAAE0.added.md", "changelog.d/01M3Z714MQBXMW4PJVRQNDWNDM.added.md", "changelog.d/01M3Z714QT3QXEAJAK9JDDEB70.changed.md", "changelog.d/01M3Z714XYJEHXHNWXKVXAYFQJ.changed.md", "changelog.d/01M3Z7151078ZAM6AM1GFWC6QP.added.md", "changelog.d/01M3Z71542Y6NZG3G8A83EFRF2.added.md", "changelog.d/01M3Z7157776CWEKRPG8886VJ4.added.md"]
+++

found while working ~46BECG2. Fetch the remote ticket branch and record a lease move event instead of reporting E-CLAIM-LOST; publish currently only recognises ancestry-of-local as resumed.
