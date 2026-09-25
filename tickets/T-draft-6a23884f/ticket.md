---
id: T-draft-6a23884f
title: 'STORE family scaffold: client-library detection, findings function, gate wiring,
  gates.md rows, registry entries'
state: queued
kind: feature
origin: agent
created: '2026-09-25'
priority: medium
parent: T-draft-8c7707f1
tier: ticket
sprint: store-family
runs_last: false
milestone: 0.538.0
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
- src/frob/store/__init__.py
- src/frob/store/_detect.py
- src/frob/store/_findings.py
- src/frob/gates/_waive.py
- docs/modules/gates.md
- docs/modules/store.md
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
Every STORE rule leaf needs three things before it can ship a finding:
(1) client-library detection deciding relevance -- `src/frob/store/
_detect.py::detect_store_clients` sniffs a repo's tracked imports for
redis/pymongo/motor/mongoose/boto3/neo4j/elasticsearch-py/clickhouse-
connect/influxdb-client, returning a `frozenset[StoreClientKind]`, empty
for a repo with none of them (mirrors `frob.webapp.detect_frameworks`'s
own shape and its owner directive verbatim: "a CLI repo with no detected
framework runs none of this work" -- here, a repo with no detected store
client runs no STORE check); (2) one shared findings dataclass
(`StoreRuleFinding`, mirroring `frob.sql._orm_rules.OrmRuleFinding`'s
`rule`/`file`/`line`/`message` shape) and one folding entry point per
Story (`store1xx_findings`, `store2xx_findings`, `store3xx_findings`)
that each per-client module's own findings function feeds into, matching
`orm_rule_findings`'s "one findings function, N rule ids" shape a gate
wires in with a single call; (3) the id-reservation block in
`docs/modules/gates.md` for every STORE10x/20x/30x id this tree assigns,
in the same "(not yet implemented) | reserved by T-STORE-EPIC ... -- no
check ships this id yet" shape the SQL101-109 rows already carry, plus
the matching `_KNOWN_GATE_RULES` entries in `src/frob/gates/_waive.py` so
`frob:waive STORExxx reason="..."` is legal syntax from the moment a
rule leaf lands, not after.

Acceptance criteria:
- `detect_store_clients(root)` returns the correct client set for a
  fixture repo importing each of the 8 client libraries, and an empty
  set for a fixture repo importing none.
- `STORE101` through `STORE305` (and `STORE101`-adjacent reserved-but-
  unshipped ids for the ones not in this tree yet) all appear in
  `docs/modules/gates.md`'s rule catalog and `_KNOWN_GATE_RULES`.
- `docs/modules/store.md` documents the family shape: tiering, per-
  client detection gate, and a pointer to
  scratchpad/db-paradigm-research.md's authority citations for anyone
  auditing a rule's sourcing later.
- No rule finding function exists yet in this leaf's scope -- that is
  every downstream leaf's own job; this leaf only wires the substrate
  every downstream leaf imports.
