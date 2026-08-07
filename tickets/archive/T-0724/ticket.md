---
id: T-0724
title: wire check_resource_contention into the production sys audit path (SYS200-203
  currently invoked by nothing)
state: done
kind: security
origin: agent
created: '2026-07-22'
priority: high
blocked_by:
- T-0699
parent: T-0331
tier: ticket
sprint: null
scope:
- src/frob/app/sys_runner.py
- src/frob/strata/**
- tests/system/test_cli_sys_plan.py
- pyproject.toml
- uv.lock
- .frob-release.json
- design/frob.strata
- src/frob/strata/_audit.py
- CHANGELOG.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: pyproject.toml
  reason: REL001 version bump to 0.90.0 required by this ticket's new public symbols
    (check_resource_contention wiring, DesignIds.store_ids)
  actor: logan
  at: '2026-07-22'
- op: add
  glob: uv.lock
  reason: REL001 version bump to 0.90.0 required by this ticket's new public symbols
    (check_resource_contention wiring, DesignIds.store_ids)
  actor: logan
  at: '2026-07-22'
- op: add
  glob: .frob-release.json
  reason: REL001 version bump to 0.90.0 required by this ticket's new public symbols
    (check_resource_contention wiring, DesignIds.store_ids)
  actor: logan
  at: '2026-07-22'
- op: add
  glob: design/frob.strata
  reason: SYS203 waivers for the reviewer-surfaced tickets_ledger findings live in
    this repo's own design model
  actor: logan
  at: '2026-07-22'
- op: add
  glob: src/frob/strata/_audit.py
  reason: 'T-0724 review round: _gap_rule_in_scope excluded SYS100-102/HOST001-002
    from its own waiver-staleness sweep but not SYS200-203, so a legitimate SYS203
    waiver was wrongly reported stale by evaluate_exhaustiveness even while check_resource_contention
    correctly applied it -- smallest possible fix per coordinator''s T-0630-overlap
    guidance, not a general _audit.py rework'
  actor: logan
  at: '2026-07-22'
- op: add
  glob: CHANGELOG.md
  reason: REL001 requires a CHANGELOG entry for each version bump this ticket's public-API/waiver
    changes forced (0.90.0, 0.91.0)
  actor: logan
  at: '2026-07-22'
evidence:
- tests/system/test_cli_sys_plan.py::TestSysAuditContentionCli::test_duplicate_port_fires_sys200_through_cli
- tests/unit/strata/test_contention.py::TestDuplicatePort::test_two_nodes_same_port_fires
designated_repro_test: null
acceptance:
- text: GIVEN a model with a duplicate-port conflict WHEN frob sys audit runs via
    the CLI THEN SYS200 appears in the command output
  evidence: []
threat: null
component: null
---
T-0699 landed SYS200-203 (duplicate port, overlapping owns/acl, shared pipe, shared store write) as a real, tested check_resource_contention -- but no CLI command invokes it (src/frob/app/** was out of its scope): the catalogued-is-not-enforced trap, disclosed honestly in its Done report. Wire it into frob sys audit (and whatever sys check surface selfconform uses) including the Module.stores id threading SYS203 needs, with a system test proving a contention fixture surfaces through the real CLI. Same class as T-0630 (G1 binding wiring) -- production invocation is the ticket, not the check.