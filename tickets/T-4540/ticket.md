---
id: T-4540
title: 'REL002 fires on every land while dev_version_bump is on: the release stamp
  cannot match a .devN version between cuts, raising quarantine and forcing synchronous
  verification'
state: in-progress
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
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: GIVEN pyproject version 0.531.1.devN with dev_version_bump = true and a release
    stamp at 0.531.0 WHEN REL002 runs THEN it reports no finding (a dev build ahead
    of the last stamp is coherent by construction)
  evidence: []
- text: GIVEN a FINAL version that does not match the stamp WHEN REL002 runs THEN
    it still fires exactly as today
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Measured 2026-09-16: after T-4493 landed (dev version 0.531.1.devN via T-4184's per-land bump), the post-land sweep raised quarantine with a single REL002 on .frob-release.json; the next land (T-4501) then ran with deferred verification OFF, a fully synchronous post-land sweep, and took 45 minutes instead of 4. REL001 already knows the dev-suffix rule (a dev build ahead of the manifest satisfies a NONE bump class); REL002's stamp-coherence check needs the same awareness: a PEP 440 dev version whose base is greater than the stamped final is coherent between cuts. Find the emitter with git grep REL002 -- src/frob; adjust scope to the real file.