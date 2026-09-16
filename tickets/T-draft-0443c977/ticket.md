---
id: T-draft-0443c977
title: frob doctor recognizes the Unity toolchain
state: queued
kind: feature
origin: agent
created: '2026-09-16'
priority: medium
parent: T-draft-e7dd275c
tier: ticket
sprint: v0.533.0
runs_last: false
milestone: v0.533.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/doctor.py
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
Teach frob doctor to detect an installed Unity Editor / Unity Hub (optional, informational -- absence is not an error) and report the detected editor version when run inside a Unity project, so a user can confirm their toolchain before running Unity batchmode test evidence (story 5).

GIVEN a machine with Unity Hub installed at its default location, WHEN frob doctor runs, THEN it reports the detected Unity editor version(s) as an informational line.
GIVEN a machine with no Unity installation, WHEN frob doctor runs inside a detected Unity project, THEN it reports Unity as not found without failing the doctor run.
GIVEN a non-Unity project, WHEN frob doctor runs, THEN it does not attempt Unity detection at all (no spurious 'Unity not found' noise for unrelated projects).