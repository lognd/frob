---
id: T-6599
title: LAYOUT001-003 consume crunk gallery check --json (stable contract) instead
  of the vendored v1 manifest schema, which misreads crunk manifest v3 and has no
  platform axis
state: queued
kind: feature
origin: agent
created: '2026-09-26'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: 0.535.0
flavour: null
due: null
rank: null
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: null
branch: null
scope:
- src/frob/gates/_layout_gate.py
- src/frob/webapp/_layout_structure.py
- src/frob/webapp/_gallery_schema.py
- docs/modules/webapp-layout-structure.md
- docs/modules/webapp-layout.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: set
  reason: DOC006 inline waivers (T-draft-7ee140de)
  actor: logan
  at: '2026-09-26'
  old_length: 2004
  new_length: 2216
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Reported by the crunk session (2026-09-26): crunk's gallery manifest moved
from v1 to v2 (T-0169) and v3 (T-0221/T-0219) today. v3 keys VerdictRecord
and RenderArtifact by (state_id, platform) with platform_hash and
<!-- frob:waive DOC006 reason="external, illustrative or future-facing path named in this ticket body" -->captured_attrs, SCHEMA_VERSION=3, schemas/gallery-manifest.v3.json, and
migrates v1/v2 on read. crunk's own gate is GALLERY001 (missing render per
cell), 002 (unapproved), 003 (expired: source, fixture or platform hash),
004 (rejected), 005 (undeclared screen); contract documented in crunk's
<!-- frob:waive DOC006 reason="external, illustrative or future-facing path named in this ticket body" -->docs/design/subsystems/gallery-manifest.md ("FROB-SIDE VENDORING NOTE").
Verified on dev 9f1474a3c1: frob's LAYOUT001-003 (T-5767) reads the
vendored v1 mirror (`_VENDORED_SCHEMA_VERSION = 1`, keyed on source_hash
only, no platform axis, review-current recomputes over source bytes
alone), so it misreads v3 manifests and cannot reopen a single platform's
cells.

Owner decision (crunk generates the gallery and manifest; frob enforces
the review gate): frob stops parsing the manifest and consumes crunk's
stable interface. Deliver: (1) LAYOUT001-003 invoke `crunk gallery check
--json` (crunk is already REQUIRED_FOR_FAMILY, T-5762) and map GALLERY001
-> LAYOUT003 (missing render), GALLERY002/004 -> LAYOUT001 (unreviewed /
rejected), GALLERY003 -> LAYOUT002 (expired, with the expiry cause and
platform in the message), GALLERY005 -> a new LAYOUT004 (undeclared
screen); rule ids and waiver targets stay stable; (2) refuse with one
clear finding when the JSON header's schema version is newer than frob
understands, instead of misreading; (3) delete the vendored v1 mirror and
its byte-hash expiry code once the JSON path is the only reader; (4)
positive control: a fixture JSON with one row per rule id produces
exactly the mapped LAYOUT findings, and a header with an unknown schema
version produces the single refusal. crunk side: the JSON row shape is
requested from crunk-ba in the same conversation; until this lands,
LAYOUT on a v3 manifest is known-wrong and may be waived per repo.
