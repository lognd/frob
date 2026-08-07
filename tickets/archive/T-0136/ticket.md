---
id: T-0136
title: 'strata surface grammar: on deploy / secret constructs unreachable from .strata
  source text'
state: done
kind: bug
origin: agent
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- strata-core/src/parse.rs
- src/frob/strata/_ast.py
- src/frob/strata/_elaborate.py
- docs/strata/surface.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_litmus_deploy_secret.py::TestDeploySecretGoldens::test_secret_desugars_to_issue_revoke_reads_flows
- tests/unit/strata/test_litmus_deploy_secret.py::TestDeploySecretGoldens::test_on_deploy_lands_on_worker_node
designated_repro_test: null
threat: null
component: null
---
Found while implementing T-0083 (std.deploy) and T-0082 (std.secrets). Same class of gap as T-0132 (code=/may unreachable): strata-core's lexer/parser have no block syntax for a canary-stage list, endorsement-chain id list, or the secret construct's issued-by/audience/lifetime clauses, so DeployContract/CanaryStage and elaborate_secret are reachable only from hand-built KernelModels today. Wire `on deploy { canary { ... }; endorsed_by ...; rollback within t }` and `secret ID { issued_by ...; audience { ... }; lifetime t }` through parse.rs -> _ast.py -> _elaborate.py, keeping every existing litmus golden byte-identical. Consolidates the surface-grammar follow-ups filed separately by the T-0082 and T-0083 implementations; do together with (or immediately after) T-0132 since the attr-value lexing work overlaps.