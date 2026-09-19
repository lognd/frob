---
id: T-4540
title: 'REL002 fires on every land while dev_version_bump is on: the release stamp
  cannot match a .devN version between cuts, raising quarantine and forcing synchronous
  verification'
state: done
kind: bug
origin: agent
created: '2026-09-16'
priority: high
parent: T-4410
tier: ticket
sprint: v0.532.0
runs_last: false
milestone: v0.532.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_release.py
- src/frob/release
- tests/unit/test_rel002_dev_suffix.py
- src/frob/gates/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/__init__.py
  reason: REL002 emitter (_rel002_coherence_violations) actually lives here, not in
    a nonexistent gates/_release.py
  actor: logan
  at: '2026-09-16'
evidence:
- tests/unit/test_rel002_dev_suffix.py::test_dev_version_ahead_of_stamp_does_not_fire_rel002
- tests/unit/test_rel002_dev_suffix.py::test_final_version_mismatch_still_fires_rel002
designated_repro_test: tests/unit/test_rel002_dev_suffix.py::test_dev_version_ahead_of_stamp_does_not_fire_rel002
acceptance:
- text: GIVEN pyproject version 0.531.1.devN with dev_version_bump = true and a release
    stamp at 0.531.0 WHEN REL002 runs THEN it reports no finding (a dev build ahead
    of the last stamp is coherent by construction)
  evidence:
  - tests/unit/test_rel002_dev_suffix.py::test_dev_version_ahead_of_stamp_does_not_fire_rel002
  - tests/unit/test_rel002_dev_suffix.py::test_final_version_mismatch_still_fires_rel002
- text: GIVEN a FINAL version that does not match the stamp WHEN REL002 runs THEN
    it still fires exactly as today
  evidence:
  - tests/unit/test_rel002_dev_suffix.py::test_final_version_mismatch_still_fires_rel002
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Measured 2026-09-16: after T-4493 landed (dev version 0.531.1.devN via T-4184's per-land bump), the post-land sweep raised quarantine with a single REL002 on .frob-release.json; the next land (T-4501) then ran with deferred verification OFF, a fully synchronous post-land sweep, and took 45 minutes instead of 4. REL001 already knows the dev-suffix rule (a dev build ahead of the manifest satisfies a NONE bump class); REL002's stamp-coherence check needs the same awareness: a PEP 440 dev version whose base is greater than the stamped final is coherent between cuts. Find the emitter with git grep REL002 -- src/frob; adjust scope to the real file.