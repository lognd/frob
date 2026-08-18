---
id: T-2462
title: defer pyproject.toml/.frob-release.json version bump to an explicit release-cut,
  matching T-2445's CHANGELOG.md fragment deferral
state: queued
kind: feature
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/__init__.py
- src/frob/app/ticket_runner/_close_cmd.py
- src/frob/app/ticket_runner/_land_cmd.py
- src/frob/release/_fragments.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-2445 landed changelog.d/T-####.md fragments so CHANGELOG.md's write is collision-free and self-healing under land interruption, but left pyproject.toml's version line and .frob-release.json's stamped manifest bumping on EVERY land, unchanged -- the other half of the measured 6-of-7-lands-touch-both-shared-files contention T-2445 was filed to close.

A fuller design defers that bump too, to an explicit release-cut (frob release assemble, or folded into frob release publish) reading the same changelog.d/ fragments' bump: header to compute the accumulated max bump class. This needs, in the same leaf (both ripple together, do not split):
- frob.gates.release_gate (REL001): the plain-root-checkout ERROR path (_rel001_version / _changelog_mentions) must learn a 'deferred via fragments, not silently missing' WARN posture, mirroring _rel001_land_owned's existing informational-not-error precedent, or every frob check on main will start erroring forever the moment nothing bumps pyproject.toml per land.
- frob.app.ticket_runner._close_cmd._own_obligations_rel_bump_dirty: the close-time REL001 preflight currently treats 'pyproject.toml already covers the diff' as the not-dirty signal; it needs to also accept 'a changelog.d/T-####.md fragment already exists for this ticket' as satisfying the obligation, or every ticket whose scope touches public API becomes permanently un-closeable between release cuts.

Not started: this ticket's own src/frob/gates/__init__.py scope was leased by a concurrent ticket (T-2435) at T-2445's dispatch time, so T-2445 deliberately scoped this half out rather than attempt it without the file. Re-check the lease before starting.