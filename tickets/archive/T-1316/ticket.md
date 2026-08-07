---
id: T-1316
title: 'docs: T-1233 residue -- cve.md/index.md stale T-0147 framing, fuzz.md default
  and --budget claims'
state: done
kind: docs
origin: agent
created: '2026-07-29'
priority: high
parent: T-1226
tier: ticket
sprint: null
scope:
- docs/modules/cve.md
- docs/modules/fuzz.md
- docs/index.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- cmd:uv run frob check --only docanchor --only docblocks --only doclink exit=0 sha256=9f385d517f7f
- cmd:uv run frob check --only docanchor --only docblocks --only doclink exit=0 sha256=f3301ec23b5f
designated_repro_test: null
acceptance:
- text: GIVEN the three residual findings from the T-1233 post-land verification THEN
    cve.md and index.md describe T-0147 (vet CVE matching) as shipped (src/frob/vet/_cve.py),
    and fuzz.md states the real [fuzz].enforce default (OFF) and puts --budget on
    frob check where it lives
  evidence:
  - cmd:uv run frob check --only docanchor --only docblocks --only doclink exit=0
    sha256=f3301ec23b5f
threat: null
component: null
---
