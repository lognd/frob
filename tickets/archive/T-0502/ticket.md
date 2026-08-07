---
id: T-0502
title: 'DOC004 console-tier burndown: anchor or waive the 59 unbound fences'
state: done
kind: docs
origin: agent
created: '2026-07-21'
priority: medium
parent: null
tier: ticket
sprint: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- cmd:uv run frob check --only docblocks exit=0 sha256=475855667bb8
designated_repro_test: null
threat: null
component: null
---
Console/bash command-drift tier (T-0443) flags 59 unbound fences across agents/**, skills/**, docs/commands/**, docs/modules/**, docs/guides/agentic-workflow.md, docs/guides/install.md. Per playbook: waive illustrative agent/skill workflow examples narrowly per-fence; bind real command reference docs with genuine anchors, fixing stale text where drifted. Skip docs/modules/gates.md (owned by sibling gates-chain agent) and src/frob/gates/** (out of scope).