+++
id = "01M5K5SWHDE7FP0FPDHQWH2ZRH"
title = "Declare danger/warning/success roles in the default crunk preset"
type = "task"
category = "in-progress"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-23T01:25:29Z"
updated = "2026-10-23T03:04:52Z"
scope = ["crates/crunk-spec/src/presets/**", "crates/crunk-spec/tests/**", "crates/crunk-rules/tests/**", "tests/crunk-parity/fixtures/e2e/e2e_12_ungoverned/**", "tests/crunk-parity/fixtures/e2e/e2e_54_pathmode/**", "crates/crunk-rules/src/rules/craft008.md", "crates/crunk-check/tests/color001.rs", "docs/reference/rules/CRAFT008.md", "docs/reference/rules/README.md", "changelog.d/01M1QDTYR2FFF5HYHVZP2W1WMP.fixed.md", "changelog.d/01M1QDTYRJ3P3GT8828GCNECVB.added.md", "changelog.d/01M1T07NW78MGWRF7HZQMPSRAV.security.md", "changelog.d/01M1T07NWAFVRT2V4RAPVJ9SQM.added.md", "changelog.d/01M1T07NX1SZYZBZYYW821FN00.added.md", "changelog.d/01M1T07NY615PQ6RAEB4CESXMT.security.md", "changelog.d/01M2VFD1ZAS7PZERWYPQDMB8GH.added.md", "changelog.d/01M2VFD1ZBJP6X2ACJ4KCF29W6.added.md", "changelog.d/01M2VFD1ZDWWNTW1FFGKHCKTS3.added.md", "changelog.d/01M3AXSDBMG2ZAEHTQ6JHA8CYK.fixed.md", "changelog.d/01M3DG64C705481E6V5X4W9S9S.fixed.md", "changelog.d/01M3DG64CFWRYVDS3DGW91G8EK.added.md", "changelog.d/01M3DG64CNAZ8K50HQ046VKHER.added.md", "changelog.d/01M3DG64ECQN5RFA286F6YXYRZ.added.md", "changelog.d/01M3Z713C4RW0T6XK1ZB7VH1B4.changed.md", "changelog.d/01M3Z7141TW2H3HXJRK1QBHP7T.added.md", "changelog.d/01M3Z714EEST9EGEHWWV56RXG4.added.md", "changelog.d/01M3Z714HJ6E02VGXH271BAAE0.added.md", "changelog.d/01M3Z714MQBXMW4PJVRQNDWNDM.added.md", "changelog.d/01M3Z714QT3QXEAJAK9JDDEB70.changed.md", "changelog.d/01M3Z7151078ZAM6AM1GFWC6QP.added.md", "changelog.d/01M3Z71542Y6NZG3G8A83EFRF2.added.md", "changelog.d/01M3Z7157776CWEKRPG8886VJ4.added.md", "changelog.d/01M3Z90E4JN2DFEJ0Y4WHCDCMG.changed.md", "changelog.d/01M3ZEH464EFCFAZ4XDKE89D5Z.changed.md", "changelog.d/01M3ZTAV8SXD9C6G4A42WY14K9.changed.md", "changelog.d/01M3ZWN5CJ3BQVBGBRG62ZYZ2M.fixed.md", "changelog.d/01M3ZX7DG5711ZSC4R0Y64C78A.changed.md", "changelog.d/01M3ZX7DMYNTWB3AP04CDMAECH.changed.md"]

[[acceptance]]
text = "Given a project initialised with the default crunk preset, when crunk check runs, then CRAFT008 reports nothing"
bound = false

[[acceptance]]
text = "Given the default preset, when its roles are listed, then danger, warning and success roles are declared"
bound = false
+++

found while working 01M5HM3W18AJZET52BZBEJFYD4: CRAFT008 now fires on the default preset, which declares only a body role; add state roles so a fresh init is clean.
