---
id: T-1008
title: 'EPIC: generate, do not hand-maintain -- auto-generate the boilerplate the
  drive kept touching by hand'
state: done
kind: feature
origin: human
created: '2026-07-27'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/**
- docs/**
- tests/test_release.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_release.py
  reason: 'epic close: evidence file per D-02 route'
  actor: logan
  at: '2026-07-27'
evidence:
- tests/test_release.py::TestReleaseGateCoherence::test_hand_edited_pyproject_fires_rel002
designated_repro_test: null
threat: null
component: null
---
User directive 2026-07-27: a lot of boilerplate gets touched up by hand (versioning being the worst offender -- three coordinator hand-repairs of the pyproject/uv.lock/.frob-release.json/CHANGELOG quartet this drive, each partial repair causing the next incident). Principle: every hand-maintained artifact that is derivable from a single source of truth becomes GENERATED, with a coherence gate so hand-edits are caught, not trusted. Children: (1) version quartet -- single-source version in the release manifest, a frob release sync command that regenerates all four artifacts, and a REL coherence error asserting they agree (the T-0992/T-1007 guard class becomes structurally unnecessary); (2) _KNOWN_GATE_RULES -- invert the T-0964 constant/literal scanner: the scan IS the registry, generated into the module (or checked as generated), with an explicit retired-ids allowlist as the only hand-maintained part; (3) check-coverage.yaml gate_rule_entries -- auto-run the existing --sync-gate-rules at land time instead of manual re-syncs (drifted twice this drive); (4) README/docs command tables -- generate from the live argparse registry so DOC005 becomes a generator check rather than a hand-sync lock. Epic closes when a full drive-style wave produces zero hand-edits of any generated artifact.