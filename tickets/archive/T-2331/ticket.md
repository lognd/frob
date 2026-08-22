---
id: T-2331
title: 'post-land sweep regression from T-2299: 32 new (rule, file) identit(ies),
  89 finding(s) (ARCH001, ARCH103, COV001, COV003)'
state: dropped
kind: bug
origin: agent
created: '2026-08-17'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: design
  reason: measurement/dispositioning only -- not fixing code in this ticket; real
    fixes tracked in child ticket, pre-existing fold-ins go to owning tickets
  actor: logan
  at: '2026-08-17'
- op: remove
  glob: docs/commands/release.md
  reason: measurement/dispositioning only -- not fixing code in this ticket; real
    fixes tracked in child ticket, pre-existing fold-ins go to owning tickets
  actor: logan
  at: '2026-08-17'
- op: remove
  glob: docs/design/gate-semantics-classification.md
  reason: measurement/dispositioning only -- not fixing code in this ticket; real
    fixes tracked in child ticket, pre-existing fold-ins go to owning tickets
  actor: logan
  at: '2026-08-17'
- op: remove
  glob: docs/guides/coordinator-scripts.md
  reason: measurement/dispositioning only -- not fixing code in this ticket; real
    fixes tracked in child ticket, pre-existing fold-ins go to owning tickets
  actor: logan
  at: '2026-08-17'
- op: remove
  glob: docs/modules/cli.md
  reason: measurement/dispositioning only -- not fixing code in this ticket; real
    fixes tracked in child ticket, pre-existing fold-ins go to owning tickets
  actor: logan
  at: '2026-08-17'
- op: remove
  glob: scripts/fleet_status.py
  reason: measurement/dispositioning only -- not fixing code in this ticket; real
    fixes tracked in child ticket, pre-existing fold-ins go to owning tickets
  actor: logan
  at: '2026-08-17'
- op: remove
  glob: src/frob/app/telemetry.py
  reason: measurement/dispositioning only -- not fixing code in this ticket; real
    fixes tracked in child ticket, pre-existing fold-ins go to owning tickets
  actor: logan
  at: '2026-08-17'
- op: remove
  glob: src/frob/app/ticket_runner/_land_cmd.py
  reason: measurement/dispositioning only -- not fixing code in this ticket; real
    fixes tracked in child ticket, pre-existing fold-ins go to owning tickets
  actor: logan
  at: '2026-08-17'
- op: remove
  glob: src/frob/app/ticket_runner/_new.py
  reason: measurement/dispositioning only -- not fixing code in this ticket; real
    fixes tracked in child ticket, pre-existing fold-ins go to owning tickets
  actor: logan
  at: '2026-08-17'
- op: remove
  glob: src/frob/app/ticket_runner/_rapid_sweep.py
  reason: measurement/dispositioning only -- not fixing code in this ticket; real
    fixes tracked in child ticket, pre-existing fold-ins go to owning tickets
  actor: logan
  at: '2026-08-17'
- op: remove
  glob: src/frob/app/verify_runner.py
  reason: measurement/dispositioning only -- not fixing code in this ticket; real
    fixes tracked in child ticket, pre-existing fold-ins go to owning tickets
  actor: logan
  at: '2026-08-17'
- op: remove
  glob: src/frob/gates/_debt_deprecated.py
  reason: measurement/dispositioning only -- not fixing code in this ticket; real
    fixes tracked in child ticket, pre-existing fold-ins go to owning tickets
  actor: logan
  at: '2026-08-17'
- op: remove
  glob: src/frob/gates/_fmt_directives.py
  reason: measurement/dispositioning only -- not fixing code in this ticket; real
    fixes tracked in child ticket, pre-existing fold-ins go to owning tickets
  actor: logan
  at: '2026-08-17'
- op: remove
  glob: src/frob/release/_cli.py
  reason: measurement/dispositioning only -- not fixing code in this ticket; real
    fixes tracked in child ticket, pre-existing fold-ins go to owning tickets
  actor: logan
  at: '2026-08-17'
- op: remove
  glob: src/frob/tickets/_land_git_ops.py
  reason: measurement/dispositioning only -- not fixing code in this ticket; real
    fixes tracked in child ticket, pre-existing fold-ins go to owning tickets
  actor: logan
  at: '2026-08-17'
- op: remove
  glob: src/frob/verify/_drain.py
  reason: measurement/dispositioning only -- not fixing code in this ticket; real
    fixes tracked in child ticket, pre-existing fold-ins go to owning tickets
  actor: logan
  at: '2026-08-17'
- op: remove
  glob: src/frob/verify/_quarantine.py
  reason: measurement/dispositioning only -- not fixing code in this ticket; real
    fixes tracked in child ticket, pre-existing fold-ins go to owning tickets
  actor: logan
  at: '2026-08-17'
- op: remove
  glob: tests/test_release.py
  reason: measurement/dispositioning only -- not fixing code in this ticket; real
    fixes tracked in child ticket, pre-existing fold-ins go to owning tickets
  actor: logan
  at: '2026-08-17'
- op: remove
  glob: tickets/T-1205
  reason: measurement/dispositioning only -- not fixing code in this ticket; real
    fixes tracked in child ticket, pre-existing fold-ins go to owning tickets
  actor: logan
  at: '2026-08-17'
- op: remove
  glob: tickets/T-1235
  reason: measurement/dispositioning only -- not fixing code in this ticket; real
    fixes tracked in child ticket, pre-existing fold-ins go to owning tickets
  actor: logan
  at: '2026-08-17'
- op: remove
  glob: tickets/T-1397
  reason: measurement/dispositioning only -- not fixing code in this ticket; real
    fixes tracked in child ticket, pre-existing fold-ins go to owning tickets
  actor: logan
  at: '2026-08-17'
- op: remove
  glob: tickets/T-1526
  reason: measurement/dispositioning only -- not fixing code in this ticket; real
    fixes tracked in child ticket, pre-existing fold-ins go to owning tickets
  actor: logan
  at: '2026-08-17'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 8181f5cdb4f7975f46a65b59be37c06c8523e363
---
The deferred post-land unscoped sweep (T-1684) for T-2299 at commit fb26e9e5891098f68c7a3669ed682f4e05750a56 found 32 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (32), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 89 actual finding(s) across those 32 identit(ies).

New (rule, file) identit(ies) filed here:

- ARCH001  src/frob/app/telemetry.py
- ARCH001  src/frob/app/ticket_runner/_land_cmd.py
- ARCH001  src/frob/app/ticket_runner/_new.py
- ARCH103  scripts/fleet_status.py
- ARCH103  src/frob/app/ticket_runner/_land_cmd.py
- ARCH103  src/frob/release/_cli.py
- COV001  scripts/fleet_status.py
- COV001  src/frob/tickets/_land_git_ops.py
- COV001  src/frob/verify/_drain.py
- COV001  src/frob/verify/_quarantine.py
- COV003  tickets/T-1205
- COV003  tickets/T-1235
- COV003  tickets/T-1397
- COV003  tickets/T-1526
- DOC001  docs/commands/release.md
- DOC002  scripts/fleet_status.py
- DOC002  src/frob/app/verify_runner.py
- DOC002  src/frob/verify/_drain.py
- DOC011  docs/design/gate-semantics-classification.md
- DOC011  docs/guides/coordinator-scripts.md
- DRIFT001  src/frob/app/ticket_runner/_rapid_sweep.py
- DRIFT001  src/frob/gates/_fmt_directives.py
- DRIFT002  scripts/fleet_status.py
- DRIFT002  src/frob/verify/_drain.py
- PERF003  src/frob/gates/_debt_deprecated.py
- PERF004  src/frob/app/ticket_runner/_land_cmd.py
- PERF004  src/frob/app/ticket_runner/_new.py
- RENDER001  src/frob/release/_cli.py
- SEC110  tests/test_release.py
- SELFAUDIT001  design
- TICK004  tickets.md
- WIRE003  docs/modules/cli.md

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- ARCH001  src/frob/app/telemetry.py  -> UNATTRIBUTED (2 batch commits' touched symbols all reach this finding); candidate commits: ['c30c384aeb1fb8d7efc02da24cd093aaaad85342', '26c27418eec2a9ce1d1e9b504afdda15a0f5c283']
- ARCH001  src/frob/app/ticket_runner/_land_cmd.py  -> UNATTRIBUTED (20 batch commits' touched symbols all reach this finding); candidate commits: ['beb1d2def761d8ddbf82d965213bea3a5cab3ffe', 'a1d37e461d4818c14af3a4a00170d60b083955ac', '5caf24a262a336d6deef5b7a61749e1a2149cc79', '0f2271017a3734245ce7ac2ba5deb5bcefaa2429', '1fbcfe328fd36724fe1350a58d6122828c5b8fdc', '8ea951cb7ce8d2578704c9c3c6cd78159851588f', '150ba1ccd26ceafef7fdbe678203300b48176979', '2d341516c3bb7e9829e88856d5dd4745748fd04f', 'a464da7a7e0fb34842a1e038d0ec7d39487226eb', 'f5568b7dbe36b3f9c2628b551814da0cab8abc5c', 'b8fab3e6e8bb80f3467587dbd37c4b52cba1a851', '948b2eee1d56a6129bb998da20985eb38f99eb4f', 'd21d2570d092c0ddde4088a577832a72b984e6e0', '8973e88837ca28a322fa8069a3268681f56c7bbb', '45e025ef7c320b97ab87bb89075342f681003cbd', '79b07fc83b5509649dfd7a04559a6d050f233bbf', '90c8e43caeb5bc6b9024acfd36d2b5e415eded57', 'a39d81cc95bcc4b1b8f2ae31751c6d751eb3eda0', '13e3026ad550af31f8f1ae45a2db98591c99c7ea', '632bc2d02c89d179614690a3d4f80bafac69170f']
- ARCH001  src/frob/app/ticket_runner/_new.py  -> UNATTRIBUTED (5 batch commits' touched symbols all reach this finding); candidate commits: ['9050729816d9343502cdc94a00f850439d5b59da', '7f8c48060c8e8b4f884db6ac13dc24379c096e73', 'b8fab3e6e8bb80f3467587dbd37c4b52cba1a851', '6edc437de9ca0977783b81be55946fc3d5fdae6c', '744953cac6e0420c9ce7ce2e30e6ff2e0596a411']
- ARCH103  scripts/fleet_status.py  -> UNATTRIBUTED (16 batch commits' touched symbols all reach this finding); candidate commits: ['f2ec5e4584336620940d035848c7e98112b9d952', '97fbf751deca456af7ce5557da8ee36cd1b94814', '630b6f866461390a15e5e085d6fb0daa6120ee16', 'd63371c86d734e51f3043c56cff473aba98b0aec', '79c0250d279166239b6b3a5fa05975b669291c3e', '0ab334af19d641a5f5356d778d060b7419bc07f8', 'f780572ec0317f778ecc7aa489940c7388bd4fc6', '4629f416fbebed3d653d38edb3d989035c2cd0dd', '9303b185d9f9dbaef73ea4209221cb00b5e74430', '59fd9c6cb27cf70c7856e94256b98cd7fd1c6919', 'fb926551fe5c331f8140a5f9cd3fd456f3093d5b', '5e7ecf2ad065247ec39fe05791fe17710858b806', '44f5e684fee971d6e4edc487d4ebf6763f2f0e27', '97f526b11061b2d124eb52fe303c46983033a717', '0a66a328a3a06aed1a2027e7637c748f109d7c80', 'c266468f1ca44d5cf78d4498d566194720a74292']
- ARCH103  src/frob/app/ticket_runner/_land_cmd.py  -> UNATTRIBUTED (20 batch commits' touched symbols all reach this finding); candidate commits: ['beb1d2def761d8ddbf82d965213bea3a5cab3ffe', 'a1d37e461d4818c14af3a4a00170d60b083955ac', '5caf24a262a336d6deef5b7a61749e1a2149cc79', '0f2271017a3734245ce7ac2ba5deb5bcefaa2429', '1fbcfe328fd36724fe1350a58d6122828c5b8fdc', '8ea951cb7ce8d2578704c9c3c6cd78159851588f', '150ba1ccd26ceafef7fdbe678203300b48176979', '2d341516c3bb7e9829e88856d5dd4745748fd04f', 'a464da7a7e0fb34842a1e038d0ec7d39487226eb', 'f5568b7dbe36b3f9c2628b551814da0cab8abc5c', 'b8fab3e6e8bb80f3467587dbd37c4b52cba1a851', '948b2eee1d56a6129bb998da20985eb38f99eb4f', 'd21d2570d092c0ddde4088a577832a72b984e6e0', '8973e88837ca28a322fa8069a3268681f56c7bbb', '45e025ef7c320b97ab87bb89075342f681003cbd', '79b07fc83b5509649dfd7a04559a6d050f233bbf', '90c8e43caeb5bc6b9024acfd36d2b5e415eded57', 'a39d81cc95bcc4b1b8f2ae31751c6d751eb3eda0', '13e3026ad550af31f8f1ae45a2db98591c99c7ea', '632bc2d02c89d179614690a3d4f80bafac69170f']
- ARCH103  src/frob/release/_cli.py  -> attributed to T-2242 (commit 9584f1fd3049, already closed/dropped -- filed below) via src/frob/release/_cli.py::add_release_publish_parser
- COV001  scripts/fleet_status.py  -> UNATTRIBUTED (16 batch commits' touched symbols all reach this finding); candidate commits: ['f2ec5e4584336620940d035848c7e98112b9d952', '97fbf751deca456af7ce5557da8ee36cd1b94814', '630b6f866461390a15e5e085d6fb0daa6120ee16', 'd63371c86d734e51f3043c56cff473aba98b0aec', '79c0250d279166239b6b3a5fa05975b669291c3e', '0ab334af19d641a5f5356d778d060b7419bc07f8', 'f780572ec0317f778ecc7aa489940c7388bd4fc6', '4629f416fbebed3d653d38edb3d989035c2cd0dd', '9303b185d9f9dbaef73ea4209221cb00b5e74430', '59fd9c6cb27cf70c7856e94256b98cd7fd1c6919', 'fb926551fe5c331f8140a5f9cd3fd456f3093d5b', '5e7ecf2ad065247ec39fe05791fe17710858b806', '44f5e684fee971d6e4edc487d4ebf6763f2f0e27', '97f526b11061b2d124eb52fe303c46983033a717', '0a66a328a3a06aed1a2027e7637c748f109d7c80', 'c266468f1ca44d5cf78d4498d566194720a74292']
- COV001  src/frob/tickets/_land_git_ops.py  -> UNATTRIBUTED (26 batch commits' touched symbols all reach this finding); candidate commits: ['76f94bccbcd19a70470a910b99a879076ccfdeb6', 'beb1d2def761d8ddbf82d965213bea3a5cab3ffe', '461302f048f3ca437e1faf1fa1e6bf5e5a3da1ab', 'a1d37e461d4818c14af3a4a00170d60b083955ac', '5caf24a262a336d6deef5b7a61749e1a2149cc79', '0f2271017a3734245ce7ac2ba5deb5bcefaa2429', '1fbcfe328fd36724fe1350a58d6122828c5b8fdc', '8ea951cb7ce8d2578704c9c3c6cd78159851588f', '150ba1ccd26ceafef7fdbe678203300b48176979', '2d341516c3bb7e9829e88856d5dd4745748fd04f', 'bc95220ec44f5703d1ef4cc4af224f3b8acf94dd', 'f5568b7dbe36b3f9c2628b551814da0cab8abc5c', 'b8fab3e6e8bb80f3467587dbd37c4b52cba1a851', '55838588a376f60cbfb81ff5a3f345a0d3d4c40c', '9fc8b80ef83ca111b2a6ba72cce081d7201573a7', 'd08758024e749f47b80131abbf83a9c4afbb6972', '948b2eee1d56a6129bb998da20985eb38f99eb4f', 'd21d2570d092c0ddde4088a577832a72b984e6e0', '8973e88837ca28a322fa8069a3268681f56c7bbb', '45e025ef7c320b97ab87bb89075342f681003cbd', 'eb88878c2ae1f95e05169aeb49cd75dfbbc4f6fd', '79b07fc83b5509649dfd7a04559a6d050f233bbf', '7788a1830a6201b7ec88020e983a79a79179cf5a', '90c8e43caeb5bc6b9024acfd36d2b5e415eded57', 'a39d81cc95bcc4b1b8f2ae31751c6d751eb3eda0', '632bc2d02c89d179614690a3d4f80bafac69170f']
- COV001  src/frob/verify/_drain.py  -> attributed to T-2310 (commit 79a3f1e911ed, already closed/dropped -- filed below) via src/frob/verify/_drain.py::DrainError
- COV001  src/frob/verify/_quarantine.py  -> UNATTRIBUTED (2 batch commits' touched symbols all reach this finding); candidate commits: ['29a2dcc9fa4e4acf47147af6c697f60e6398766c', 'b592fdd93a23630ad7c5041204c7dcc3d6ca3a7e']
- COV003  tickets/T-1205  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV003  tickets/T-1235  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV003  tickets/T-1397  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV003  tickets/T-1526  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DOC001  docs/commands/release.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DOC002  scripts/fleet_status.py  -> UNATTRIBUTED (16 batch commits' touched symbols all reach this finding); candidate commits: ['f2ec5e4584336620940d035848c7e98112b9d952', '97fbf751deca456af7ce5557da8ee36cd1b94814', '630b6f866461390a15e5e085d6fb0daa6120ee16', 'd63371c86d734e51f3043c56cff473aba98b0aec', '79c0250d279166239b6b3a5fa05975b669291c3e', '0ab334af19d641a5f5356d778d060b7419bc07f8', 'f780572ec0317f778ecc7aa489940c7388bd4fc6', '4629f416fbebed3d653d38edb3d989035c2cd0dd', '9303b185d9f9dbaef73ea4209221cb00b5e74430', '59fd9c6cb27cf70c7856e94256b98cd7fd1c6919', 'fb926551fe5c331f8140a5f9cd3fd456f3093d5b', '5e7ecf2ad065247ec39fe05791fe17710858b806', '44f5e684fee971d6e4edc487d4ebf6763f2f0e27', '97f526b11061b2d124eb52fe303c46983033a717', '0a66a328a3a06aed1a2027e7637c748f109d7c80', 'c266468f1ca44d5cf78d4498d566194720a74292']
- DOC002  src/frob/app/verify_runner.py  -> UNATTRIBUTED (4 batch commits' touched symbols all reach this finding); candidate commits: ['29a2dcc9fa4e4acf47147af6c697f60e6398766c', '7f1e45b4b5317bc55cf4b6a33f12dc794af9b53e', '13e3026ad550af31f8f1ae45a2db98591c99c7ea', '79a3f1e911ed11cb3b89dd2e34e42f6e87b40216']
- DOC002  src/frob/verify/_drain.py  -> attributed to T-2310 (commit 79a3f1e911ed, already closed/dropped -- filed below) via src/frob/verify/_drain.py::DrainError
- DOC011  docs/design/gate-semantics-classification.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DOC011  docs/guides/coordinator-scripts.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DRIFT001  src/frob/app/ticket_runner/_rapid_sweep.py  -> UNATTRIBUTED (5 batch commits' touched symbols all reach this finding); candidate commits: ['9b53f81e11e42f22f837df56517ab0139d13ebab', 'b8fab3e6e8bb80f3467587dbd37c4b52cba1a851', 'f610b31f60272f70bf7dbd136bccb63a942d14d1', '79a3f1e911ed11cb3b89dd2e34e42f6e87b40216', 'b592fdd93a23630ad7c5041204c7dcc3d6ca3a7e']
- DRIFT001  src/frob/gates/_fmt_directives.py  -> attributed to T-2298 (commit b7e69ec7a6b9, already closed/dropped -- filed below) via src/frob/gates/_fmt_directives.py::_TEST_CORPUS_SUFFIXES
- DRIFT002  scripts/fleet_status.py  -> UNATTRIBUTED (16 batch commits' touched symbols all reach this finding); candidate commits: ['f2ec5e4584336620940d035848c7e98112b9d952', '97fbf751deca456af7ce5557da8ee36cd1b94814', '630b6f866461390a15e5e085d6fb0daa6120ee16', 'd63371c86d734e51f3043c56cff473aba98b0aec', '79c0250d279166239b6b3a5fa05975b669291c3e', '0ab334af19d641a5f5356d778d060b7419bc07f8', 'f780572ec0317f778ecc7aa489940c7388bd4fc6', '4629f416fbebed3d653d38edb3d989035c2cd0dd', '9303b185d9f9dbaef73ea4209221cb00b5e74430', '59fd9c6cb27cf70c7856e94256b98cd7fd1c6919', 'fb926551fe5c331f8140a5f9cd3fd456f3093d5b', '5e7ecf2ad065247ec39fe05791fe17710858b806', '44f5e684fee971d6e4edc487d4ebf6763f2f0e27', '97f526b11061b2d124eb52fe303c46983033a717', '0a66a328a3a06aed1a2027e7637c748f109d7c80', 'c266468f1ca44d5cf78d4498d566194720a74292']
- DRIFT002  src/frob/verify/_drain.py  -> attributed to T-2310 (commit 79a3f1e911ed, already closed/dropped -- filed below) via src/frob/verify/_drain.py::DrainError
- PERF003  src/frob/gates/_debt_deprecated.py  -> attributed to T-2178 (commit d6d91f5ac217, already closed/dropped -- filed below) via src/frob/gates/_debt_deprecated.py::_DeprecatedRefIndex
- PERF004  src/frob/app/ticket_runner/_land_cmd.py  -> UNATTRIBUTED (20 batch commits' touched symbols all reach this finding); candidate commits: ['beb1d2def761d8ddbf82d965213bea3a5cab3ffe', 'a1d37e461d4818c14af3a4a00170d60b083955ac', '5caf24a262a336d6deef5b7a61749e1a2149cc79', '0f2271017a3734245ce7ac2ba5deb5bcefaa2429', '1fbcfe328fd36724fe1350a58d6122828c5b8fdc', '8ea951cb7ce8d2578704c9c3c6cd78159851588f', '150ba1ccd26ceafef7fdbe678203300b48176979', '2d341516c3bb7e9829e88856d5dd4745748fd04f', 'a464da7a7e0fb34842a1e038d0ec7d39487226eb', 'f5568b7dbe36b3f9c2628b551814da0cab8abc5c', 'b8fab3e6e8bb80f3467587dbd37c4b52cba1a851', '948b2eee1d56a6129bb998da20985eb38f99eb4f', 'd21d2570d092c0ddde4088a577832a72b984e6e0', '8973e88837ca28a322fa8069a3268681f56c7bbb', '45e025ef7c320b97ab87bb89075342f681003cbd', '79b07fc83b5509649dfd7a04559a6d050f233bbf', '90c8e43caeb5bc6b9024acfd36d2b5e415eded57', 'a39d81cc95bcc4b1b8f2ae31751c6d751eb3eda0', '13e3026ad550af31f8f1ae45a2db98591c99c7ea', '632bc2d02c89d179614690a3d4f80bafac69170f']
- PERF004  src/frob/app/ticket_runner/_new.py  -> UNATTRIBUTED (5 batch commits' touched symbols all reach this finding); candidate commits: ['9050729816d9343502cdc94a00f850439d5b59da', '7f8c48060c8e8b4f884db6ac13dc24379c096e73', 'b8fab3e6e8bb80f3467587dbd37c4b52cba1a851', '6edc437de9ca0977783b81be55946fc3d5fdae6c', '744953cac6e0420c9ce7ce2e30e6ff2e0596a411']
- RENDER001  src/frob/release/_cli.py  -> attributed to T-2242 (commit 9584f1fd3049, already closed/dropped -- filed below) via src/frob/release/_cli.py::add_release_publish_parser
- SEC110  tests/test_release.py  -> attributed to T-2242 (commit 9584f1fd3049, already closed/dropped -- filed below) via tests/test_release.py::TestAddReleasePublishParser
- SELFAUDIT001  design  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- TICK004  tickets.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- WIRE003  docs/modules/cli.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

## Drop reason
- 2026-08-17: 27/32 claimed identities genuinely reproduce, 5/32 stale (see Done report); real work is a multi-file refactor filed as child (renumbers at land); pre-existing findings already attributed to closed tickets T-2242/T-2310/T-2178 recorded in Done report; dropping this auto-filed sweep ticket in favor of the properly-scoped child rather than forcing a fix through (absorbed by T-2341)