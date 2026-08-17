---
id: T-2293
title: 'post-land sweep regression from T-2116, T-2269: 28 new (rule, file) identit(ies),
  49 finding(s) (ARCH001, ARCH103, COV001, COV003)'
state: queued
kind: bug
origin: agent
created: '2026-08-17'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- design
- docs/commands/release.md
- docs/design/gate-semantics-classification.md
- docs/guides/coordinator-scripts.md
- scripts/fleet_status.py
- src/frob/app/telemetry.py
- src/frob/app/ticket_runner/_land_cmd.py
- src/frob/app/ticket_runner/_new.py
- src/frob/app/ticket_runner/_rapid_sweep.py
- src/frob/lang/_nodes.py
- src/frob/release/_cli.py
- src/frob/tickets/_land_git_ops.py
- tests/test_release.py
- tests/test_ticket_land.py
- tests/test_ticket_work_and_land_finish.py
- tickets.md
- tickets/T-1205
- tickets/T-1235
- tickets/T-1397
- tickets/T-1526
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
The deferred post-land unscoped sweep (T-1684) for T-2116, T-2269 at commit ca7de73131a6d14681125e40e96ab50de9c61b0c found 28 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (28), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 49 actual finding(s) across those 28 identit(ies).

New (rule, file) identit(ies) filed here:

- ARCH001  src/frob/app/telemetry.py
- ARCH001  src/frob/app/ticket_runner/_land_cmd.py
- ARCH001  src/frob/app/ticket_runner/_new.py
- ARCH103  scripts/fleet_status.py
- ARCH103  src/frob/app/ticket_runner/_land_cmd.py
- ARCH103  src/frob/release/_cli.py
- COV001  src/frob/tickets/_land_git_ops.py
- COV003  tickets/T-1205
- COV003  tickets/T-1235
- COV003  tickets/T-1397
- COV003  tickets/T-1526
- DOC001  docs/commands/release.md
- DOC011  docs/design/gate-semantics-classification.md
- DOC011  docs/guides/coordinator-scripts.md
- DRIFT001  src/frob/app/ticket_runner/_rapid_sweep.py
- DRIFT001  src/frob/lang/_nodes.py
- DRIFT002  scripts/fleet_status.py
- E402  scripts/fleet_status.py
- E501  scripts/fleet_status.py
- E501  src/frob/lang/_nodes.py
- F541  tests/test_ticket_work_and_land_finish.py
- F841  tests/test_ticket_land.py
- PERF004  src/frob/app/ticket_runner/_land_cmd.py
- RENDER001  src/frob/release/_cli.py
- SEC110  tests/test_release.py
- SELFAUDIT001  design
- TEST010  tests/test_ticket_work_and_land_finish.py
- TICK004  tickets.md

T-2009: 2 lands (T-2116, T-2269) landed between the previous sweep's baseline and the commit THIS sweep actually measured (the sweep is deliberately detached, off the land critical path -- T-1684 -- so other agents' lands can land in the window before it runs). Which specific land introduced which finding below could not be determined without re-measuring at each intermediate commit; this ticket is filed against all of them rather than falsely pinned on T-2116, T-2269 alone (the one that happened to spawn this sweep process).

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- ARCH001  src/frob/app/telemetry.py  -> UNATTRIBUTED (2 batch commits' touched symbols all reach this finding); candidate commits: ['c30c384aeb1fb8d7efc02da24cd093aaaad85342', '26c27418eec2a9ce1d1e9b504afdda15a0f5c283']
- ARCH001  src/frob/app/ticket_runner/_land_cmd.py  -> UNATTRIBUTED (16 batch commits' touched symbols all reach this finding); candidate commits: ['beb1d2def761d8ddbf82d965213bea3a5cab3ffe', 'a1d37e461d4818c14af3a4a00170d60b083955ac', '5caf24a262a336d6deef5b7a61749e1a2149cc79', '0f2271017a3734245ce7ac2ba5deb5bcefaa2429', '1fbcfe328fd36724fe1350a58d6122828c5b8fdc', '8ea951cb7ce8d2578704c9c3c6cd78159851588f', '150ba1ccd26ceafef7fdbe678203300b48176979', '2d341516c3bb7e9829e88856d5dd4745748fd04f', 'a464da7a7e0fb34842a1e038d0ec7d39487226eb', 'f5568b7dbe36b3f9c2628b551814da0cab8abc5c', 'b8fab3e6e8bb80f3467587dbd37c4b52cba1a851', '948b2eee1d56a6129bb998da20985eb38f99eb4f', 'd21d2570d092c0ddde4088a577832a72b984e6e0', '8973e88837ca28a322fa8069a3268681f56c7bbb', '45e025ef7c320b97ab87bb89075342f681003cbd', '79b07fc83b5509649dfd7a04559a6d050f233bbf']
- ARCH001  src/frob/app/ticket_runner/_new.py  -> UNATTRIBUTED (3 batch commits' touched symbols all reach this finding); candidate commits: ['9050729816d9343502cdc94a00f850439d5b59da', '7f8c48060c8e8b4f884db6ac13dc24379c096e73', 'b8fab3e6e8bb80f3467587dbd37c4b52cba1a851']
- ARCH103  scripts/fleet_status.py  -> UNATTRIBUTED (15 batch commits' touched symbols all reach this finding); candidate commits: ['f2ec5e4584336620940d035848c7e98112b9d952', '97fbf751deca456af7ce5557da8ee36cd1b94814', '630b6f866461390a15e5e085d6fb0daa6120ee16', 'd63371c86d734e51f3043c56cff473aba98b0aec', '79c0250d279166239b6b3a5fa05975b669291c3e', '0ab334af19d641a5f5356d778d060b7419bc07f8', 'f780572ec0317f778ecc7aa489940c7388bd4fc6', '4629f416fbebed3d653d38edb3d989035c2cd0dd', '9303b185d9f9dbaef73ea4209221cb00b5e74430', '59fd9c6cb27cf70c7856e94256b98cd7fd1c6919', 'fb926551fe5c331f8140a5f9cd3fd456f3093d5b', '5e7ecf2ad065247ec39fe05791fe17710858b806', '44f5e684fee971d6e4edc487d4ebf6763f2f0e27', '97f526b11061b2d124eb52fe303c46983033a717', '0a66a328a3a06aed1a2027e7637c748f109d7c80']
- ARCH103  src/frob/app/ticket_runner/_land_cmd.py  -> UNATTRIBUTED (16 batch commits' touched symbols all reach this finding); candidate commits: ['beb1d2def761d8ddbf82d965213bea3a5cab3ffe', 'a1d37e461d4818c14af3a4a00170d60b083955ac', '5caf24a262a336d6deef5b7a61749e1a2149cc79', '0f2271017a3734245ce7ac2ba5deb5bcefaa2429', '1fbcfe328fd36724fe1350a58d6122828c5b8fdc', '8ea951cb7ce8d2578704c9c3c6cd78159851588f', '150ba1ccd26ceafef7fdbe678203300b48176979', '2d341516c3bb7e9829e88856d5dd4745748fd04f', 'a464da7a7e0fb34842a1e038d0ec7d39487226eb', 'f5568b7dbe36b3f9c2628b551814da0cab8abc5c', 'b8fab3e6e8bb80f3467587dbd37c4b52cba1a851', '948b2eee1d56a6129bb998da20985eb38f99eb4f', 'd21d2570d092c0ddde4088a577832a72b984e6e0', '8973e88837ca28a322fa8069a3268681f56c7bbb', '45e025ef7c320b97ab87bb89075342f681003cbd', '79b07fc83b5509649dfd7a04559a6d050f233bbf']
- ARCH103  src/frob/release/_cli.py  -> attributed to T-2242 (commit 9584f1fd3049, already closed/dropped -- filed below) via src/frob/release/_cli.py::add_release_publish_parser
- COV001  src/frob/tickets/_land_git_ops.py  -> UNATTRIBUTED (22 batch commits' touched symbols all reach this finding); candidate commits: ['76f94bccbcd19a70470a910b99a879076ccfdeb6', 'beb1d2def761d8ddbf82d965213bea3a5cab3ffe', '461302f048f3ca437e1faf1fa1e6bf5e5a3da1ab', 'a1d37e461d4818c14af3a4a00170d60b083955ac', '5caf24a262a336d6deef5b7a61749e1a2149cc79', '0f2271017a3734245ce7ac2ba5deb5bcefaa2429', '1fbcfe328fd36724fe1350a58d6122828c5b8fdc', '8ea951cb7ce8d2578704c9c3c6cd78159851588f', '150ba1ccd26ceafef7fdbe678203300b48176979', '2d341516c3bb7e9829e88856d5dd4745748fd04f', 'bc95220ec44f5703d1ef4cc4af224f3b8acf94dd', 'f5568b7dbe36b3f9c2628b551814da0cab8abc5c', 'b8fab3e6e8bb80f3467587dbd37c4b52cba1a851', '55838588a376f60cbfb81ff5a3f345a0d3d4c40c', '9fc8b80ef83ca111b2a6ba72cce081d7201573a7', 'd08758024e749f47b80131abbf83a9c4afbb6972', '948b2eee1d56a6129bb998da20985eb38f99eb4f', 'd21d2570d092c0ddde4088a577832a72b984e6e0', '8973e88837ca28a322fa8069a3268681f56c7bbb', '45e025ef7c320b97ab87bb89075342f681003cbd', 'eb88878c2ae1f95e05169aeb49cd75dfbbc4f6fd', '79b07fc83b5509649dfd7a04559a6d050f233bbf']
- COV003  tickets/T-1205  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV003  tickets/T-1235  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV003  tickets/T-1397  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV003  tickets/T-1526  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DOC001  docs/commands/release.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DOC011  docs/design/gate-semantics-classification.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DOC011  docs/guides/coordinator-scripts.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DRIFT001  src/frob/app/ticket_runner/_rapid_sweep.py  -> UNATTRIBUTED (3 batch commits' touched symbols all reach this finding); candidate commits: ['9b53f81e11e42f22f837df56517ab0139d13ebab', 'b8fab3e6e8bb80f3467587dbd37c4b52cba1a851', 'f610b31f60272f70bf7dbd136bccb63a942d14d1']
- DRIFT001  src/frob/lang/_nodes.py  -> attributed to T-2195 (commit 808e0c6fb3f4, already closed/dropped -- filed below) via src/frob/lang/_nodes.py::_declared_python_source_roots
- DRIFT002  scripts/fleet_status.py  -> UNATTRIBUTED (15 batch commits' touched symbols all reach this finding); candidate commits: ['f2ec5e4584336620940d035848c7e98112b9d952', '97fbf751deca456af7ce5557da8ee36cd1b94814', '630b6f866461390a15e5e085d6fb0daa6120ee16', 'd63371c86d734e51f3043c56cff473aba98b0aec', '79c0250d279166239b6b3a5fa05975b669291c3e', '0ab334af19d641a5f5356d778d060b7419bc07f8', 'f780572ec0317f778ecc7aa489940c7388bd4fc6', '4629f416fbebed3d653d38edb3d989035c2cd0dd', '9303b185d9f9dbaef73ea4209221cb00b5e74430', '59fd9c6cb27cf70c7856e94256b98cd7fd1c6919', 'fb926551fe5c331f8140a5f9cd3fd456f3093d5b', '5e7ecf2ad065247ec39fe05791fe17710858b806', '44f5e684fee971d6e4edc487d4ebf6763f2f0e27', '97f526b11061b2d124eb52fe303c46983033a717', '0a66a328a3a06aed1a2027e7637c748f109d7c80']
- E402  scripts/fleet_status.py  -> UNATTRIBUTED (15 batch commits' touched symbols all reach this finding); candidate commits: ['f2ec5e4584336620940d035848c7e98112b9d952', '97fbf751deca456af7ce5557da8ee36cd1b94814', '630b6f866461390a15e5e085d6fb0daa6120ee16', 'd63371c86d734e51f3043c56cff473aba98b0aec', '79c0250d279166239b6b3a5fa05975b669291c3e', '0ab334af19d641a5f5356d778d060b7419bc07f8', 'f780572ec0317f778ecc7aa489940c7388bd4fc6', '4629f416fbebed3d653d38edb3d989035c2cd0dd', '9303b185d9f9dbaef73ea4209221cb00b5e74430', '59fd9c6cb27cf70c7856e94256b98cd7fd1c6919', 'fb926551fe5c331f8140a5f9cd3fd456f3093d5b', '5e7ecf2ad065247ec39fe05791fe17710858b806', '44f5e684fee971d6e4edc487d4ebf6763f2f0e27', '97f526b11061b2d124eb52fe303c46983033a717', '0a66a328a3a06aed1a2027e7637c748f109d7c80']
- E501  scripts/fleet_status.py  -> UNATTRIBUTED (15 batch commits' touched symbols all reach this finding); candidate commits: ['f2ec5e4584336620940d035848c7e98112b9d952', '97fbf751deca456af7ce5557da8ee36cd1b94814', '630b6f866461390a15e5e085d6fb0daa6120ee16', 'd63371c86d734e51f3043c56cff473aba98b0aec', '79c0250d279166239b6b3a5fa05975b669291c3e', '0ab334af19d641a5f5356d778d060b7419bc07f8', 'f780572ec0317f778ecc7aa489940c7388bd4fc6', '4629f416fbebed3d653d38edb3d989035c2cd0dd', '9303b185d9f9dbaef73ea4209221cb00b5e74430', '59fd9c6cb27cf70c7856e94256b98cd7fd1c6919', 'fb926551fe5c331f8140a5f9cd3fd456f3093d5b', '5e7ecf2ad065247ec39fe05791fe17710858b806', '44f5e684fee971d6e4edc487d4ebf6763f2f0e27', '97f526b11061b2d124eb52fe303c46983033a717', '0a66a328a3a06aed1a2027e7637c748f109d7c80']
- E501  src/frob/lang/_nodes.py  -> attributed to T-2195 (commit 808e0c6fb3f4, already closed/dropped -- filed below) via src/frob/lang/_nodes.py::_declared_python_source_roots
- F541  tests/test_ticket_work_and_land_finish.py  -> UNATTRIBUTED (7 batch commits' touched symbols all reach this finding); candidate commits: ['a1d37e461d4818c14af3a4a00170d60b083955ac', '0f2271017a3734245ce7ac2ba5deb5bcefaa2429', '150ba1ccd26ceafef7fdbe678203300b48176979', '2d341516c3bb7e9829e88856d5dd4745748fd04f', '948b2eee1d56a6129bb998da20985eb38f99eb4f', 'd21d2570d092c0ddde4088a577832a72b984e6e0', '45e025ef7c320b97ab87bb89075342f681003cbd']
- F841  tests/test_ticket_land.py  -> UNATTRIBUTED (6 batch commits' touched symbols all reach this finding); candidate commits: ['1fbcfe328fd36724fe1350a58d6122828c5b8fdc', '8ea951cb7ce8d2578704c9c3c6cd78159851588f', 'f5568b7dbe36b3f9c2628b551814da0cab8abc5c', 'd08758024e749f47b80131abbf83a9c4afbb6972', '2cd92a86ff3e813392f26f69f36a345d4fc0c6ca', '79b07fc83b5509649dfd7a04559a6d050f233bbf']
- PERF004  src/frob/app/ticket_runner/_land_cmd.py  -> UNATTRIBUTED (16 batch commits' touched symbols all reach this finding); candidate commits: ['beb1d2def761d8ddbf82d965213bea3a5cab3ffe', 'a1d37e461d4818c14af3a4a00170d60b083955ac', '5caf24a262a336d6deef5b7a61749e1a2149cc79', '0f2271017a3734245ce7ac2ba5deb5bcefaa2429', '1fbcfe328fd36724fe1350a58d6122828c5b8fdc', '8ea951cb7ce8d2578704c9c3c6cd78159851588f', '150ba1ccd26ceafef7fdbe678203300b48176979', '2d341516c3bb7e9829e88856d5dd4745748fd04f', 'a464da7a7e0fb34842a1e038d0ec7d39487226eb', 'f5568b7dbe36b3f9c2628b551814da0cab8abc5c', 'b8fab3e6e8bb80f3467587dbd37c4b52cba1a851', '948b2eee1d56a6129bb998da20985eb38f99eb4f', 'd21d2570d092c0ddde4088a577832a72b984e6e0', '8973e88837ca28a322fa8069a3268681f56c7bbb', '45e025ef7c320b97ab87bb89075342f681003cbd', '79b07fc83b5509649dfd7a04559a6d050f233bbf']
- RENDER001  src/frob/release/_cli.py  -> attributed to T-2242 (commit 9584f1fd3049, already closed/dropped -- filed below) via src/frob/release/_cli.py::add_release_publish_parser
- SEC110  tests/test_release.py  -> attributed to T-2242 (commit 9584f1fd3049, already closed/dropped -- filed below) via tests/test_release.py::TestAddReleasePublishParser
- SELFAUDIT001  design  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- TEST010  tests/test_ticket_work_and_land_finish.py  -> UNATTRIBUTED (7 batch commits' touched symbols all reach this finding); candidate commits: ['a1d37e461d4818c14af3a4a00170d60b083955ac', '0f2271017a3734245ce7ac2ba5deb5bcefaa2429', '150ba1ccd26ceafef7fdbe678203300b48176979', '2d341516c3bb7e9829e88856d5dd4745748fd04f', '948b2eee1d56a6129bb998da20985eb38f99eb4f', 'd21d2570d092c0ddde4088a577832a72b984e6e0', '45e025ef7c320b97ab87bb89075342f681003cbd']
- TICK004  tickets.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.