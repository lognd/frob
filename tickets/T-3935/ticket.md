---
id: T-3935
title: 'ALPHA BLOCKER: frob wheel is uninstallable -- frob-core/strata-core hard-pinned
  but in no registry'
state: in-progress
kind: bug
origin: human
created: '2026-09-05'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .github/workflows/ci.yml
- .github/workflows/release.yml
- scripts/artifact_smoke.py
- tests/system/test_artifact_smoke.py
- tests/unit/test_artifact_smoke_script.py
evidence_scope:
- docs/guides/release.md
- scripts/verify_release_ci_status.py
- src/frob/doctor.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/system/test_artifact_smoke.py
  reason: 'scope closure: these are the tests that cover scripts/artifact_smoke.py
    and are the ones currently red; the fix must edit them'
  actor: logan
  at: '2026-09-05'
- op: add
  glob: tests/unit/test_artifact_smoke_script.py
  reason: 'scope closure: these are the tests that cover scripts/artifact_smoke.py
    and are the ones currently red; the fix must edit them'
  actor: logan
  at: '2026-09-05'
- op: add
  glob: docs/guides/release.md
  reason: T-3935's new artifact_smoke.py preflight (_require_core_wheels) cites the
    existing artifact-smoke-stage-t-3884 doc anchor via frob:doc; SCOPE002 requires
    the anchor target in scope even though the doc text itself is unedited
  actor: logan
  at: '2026-09-05'
- op: remove
  glob: docs/guides/release.md
  reason: 'reverting: doc-closure pulled in unrelated release.md anchors (verify_release_ci_status.py,
    doctor.py) outside this tickets scope; dropping the frob:doc citation instead
    of widening scope further'
  actor: logan
  at: '2026-09-05'
- op: add
  glob: docs/guides/release.md
  reason: scripts/artifact_smoke.py (already in scope) has pre-existing frob:doc anchors
    into docs/guides/release.md; SCOPE002 doc-closure requires the whole anchor target
    set (including two unrelated symbols this doc also anchors) in scope even though
    only the artifact-smoke-stage-t-3884 section is actually touched by this ticket
  actor: logan
  at: '2026-09-05'
- op: add
  glob: scripts/verify_release_ci_status.py
  reason: scripts/artifact_smoke.py (already in scope) has pre-existing frob:doc anchors
    into docs/guides/release.md; SCOPE002 doc-closure requires the whole anchor target
    set (including two unrelated symbols this doc also anchors) in scope even though
    only the artifact-smoke-stage-t-3884 section is actually touched by this ticket
  actor: logan
  at: '2026-09-05'
- op: add
  glob: src/frob/doctor.py
  reason: scripts/artifact_smoke.py (already in scope) has pre-existing frob:doc anchors
    into docs/guides/release.md; SCOPE002 doc-closure requires the whole anchor target
    set (including two unrelated symbols this doc also anchors) in scope even though
    only the artifact-smoke-stage-t-3884 section is actually touched by this ticket
  actor: logan
  at: '2026-09-05'
- op: remove
  glob: docs/guides/release.md
  reason: 'reverting the scope-closure spiral: adding the doc file transitively demanded
    unrelated files (docs/guides/install.md, docs/modules/cli.md, ...) neither this
    ticket nor its diff touches; dropping the new frob:doc citation on _require_core_wheels
    instead'
  actor: logan
  at: '2026-09-05'
- op: remove
  glob: scripts/verify_release_ci_status.py
  reason: 'reverting the scope-closure spiral: adding the doc file transitively demanded
    unrelated files (docs/guides/install.md, docs/modules/cli.md, ...) neither this
    ticket nor its diff touches; dropping the new frob:doc citation on _require_core_wheels
    instead'
  actor: logan
  at: '2026-09-05'
- op: remove
  glob: src/frob/doctor.py
  reason: 'reverting the scope-closure spiral: adding the doc file transitively demanded
    unrelated files (docs/guides/install.md, docs/modules/cli.md, ...) neither this
    ticket nor its diff touches; dropping the new frob:doc citation on _require_core_wheels
    instead'
  actor: logan
  at: '2026-09-05'
- op: add
  glob: docs/guides/release.md
  reason: docs/guides/release.md holds the frob:doc anchor scripts/artifact_smoke.py
    already cites (T-3884); adding to satisfy SCOPE002 doc-anchor closure, then demoting
    to evidence-only in the next call since it is only cited, never edited
  actor: logan
  at: '2026-09-05'
- op: remove
  glob: docs/guides/release.md
  reason: docs/guides/release.md is cited (frob:doc anchor target) but never edited
    by this ticket; evidence-only avoids a write lease this ticket does not use and
    (measured) avoids the full write-scope doc-closure recursion that otherwise pulls
    in every other unrelated symbol this large doc also anchors
  actor: logan
  at: '2026-09-05'
- op: add
  glob: docs/guides/release.md
  reason: scripts/artifact_smoke.py (already in scope) has pre-existing frob:doc anchors
    into this file (T-3884); SCOPE002 requires the full doc file in scope even though
    this ticket only cites the artifact-smoke-stage-t-3884 section
  actor: logan
  at: '2026-09-05'
- op: add
  glob: scripts/verify_release_ci_status.py
  reason: docs/guides/release.md (in full scope for artifact_smoke.py frob:doc closure)
    also anchors these two files elsewhere in the doc; adding to close SCOPE002, will
    demote to evidence-only next since neither is edited by this ticket
  actor: logan
  at: '2026-09-06'
- op: add
  glob: src/frob/doctor.py
  reason: docs/guides/release.md (in full scope for artifact_smoke.py frob:doc closure)
    also anchors these two files elsewhere in the doc; adding to close SCOPE002, will
    demote to evidence-only next since neither is edited by this ticket
  actor: logan
  at: '2026-09-06'
- op: remove
  glob: scripts/verify_release_ci_status.py
  reason: neither file is edited by this ticket -- pulled in only by docs/guides/release.md
    doc-anchor closure; evidence-only avoids an unused write lease and (to be verified)
    the deeper install.md/cli.md closure recursion
  actor: logan
  at: '2026-09-06'
- op: remove
  glob: src/frob/doctor.py
  reason: neither file is edited by this ticket -- pulled in only by docs/guides/release.md
    doc-anchor closure; evidence-only avoids an unused write lease and (to be verified)
    the deeper install.md/cli.md closure recursion
  actor: logan
  at: '2026-09-06'
- op: remove
  glob: docs/guides/release.md
  reason: 'reverting: this doc-closure chain is pre-existing (SmokeCheckError etc
    already had frob:doc into release.md before T-3935 existed) and spirals into unrelated
    docs/guides/install.md, docs/modules/cli.md via other unrelated symbols in the
    same shared doc/file; filing a separate ticket for the structural gap rather than
    forcing an ever-widening scope onto T-3935'
  actor: logan
  at: '2026-09-06'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED in CI run 34005559354. The standalone-install job fails outright:

  Because frob-core was not found in the package registry and
  frob==0.530.0 depends on frob-core==0.530.0, we can conclude that
  frob==0.530.0 cannot be used.

and the same cause reds three tests in tests/system/test_artifact_smoke.py on ubuntu and macOS (macOS names strata-core for macosx_11_0_arm64).

CAUSE. T-3845 made the two maturin cores DEFAULT dependencies with a hard == pin. That is the right dependency shape, but neither core is published anywhere, so any resolution that goes to a registry cannot succeed. Building the pure-python wheel is not enough: nothing in CI builds or supplies the core wheels to the installing resolver.

THIS IS EXACTLY THE STANDING ALPHA REQUIREMENT: the strata-core and frob-core maturin packages must be wheeled and grabbed automatically whenever a release is cut. Today they are neither.

WHAT TO BUILD.
1. Build both core wheels for the target platform in CI before any install-the-artifact step, and point the installing resolver at them (a local find-links index over the built dist, not a network registry).
2. Apply the same in the release workflow so a cut release ships core wheels alongside the frob wheel. artifact-smoke must prove the REAL install path; right now it proves a path no consumer can follow.
3. artifact_smoke.py must fail with a message that NAMES the missing core and says it was not supplied, rather than surfacing a raw resolver trace. A smoke check that cannot distinguish 'core not built' from 'pin is wrong' is a silent zero in the release gate.

DO NOT fix this by loosening the == pin or moving the cores back to an extra. The pin is deliberate (T-3845) and the coupling is real; the defect is that CI never supplies what the pin demands.

ACCEPTANCE
- standalone-install passes on ubuntu.
- The three artifact-smoke tests pass on ubuntu and macOS.
- The release workflow produces core wheels as published artifacts, verified by inspecting the workflow's artifact list -- do not reason about it.
- A must-fire fixture: a smoke run with the cores deliberately absent reports the named core as missing.