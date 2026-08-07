---
id: T-0326
title: 'REL001: breaking change in 0.x must bump minor, not force 1.0.0 (semver section
  4)'
state: done
kind: bug
origin: agent
created: '2026-07-19'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/release/**
- tests/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_release.py::test_breaking_change_in_0x_bumps_minor_not_to_1_0_0
designated_repro_test: null
acceptance:
- text: given a repo at 0.y.z, when a breaking public-API change is made, then REL001
    requires 0.(y+1).0 (minor bump), NOT >= 1.0.0 -- staying in 0.x per semver section
    4 (initial development)
  evidence: []
- text: given a repo at >=1.0.0, when a breaking change is made, then REL001 still
    requires a major bump
  evidence: []
threat: null
component: null
---
Hit live 2026-07-19: accumulated public-API changes since the 0.10.0 stamp (T-0179/0195/0222/0289) made frob release check demand '>= 1.0.0', which conflicts with the user's explicit policy (stay 0.x until zero tickets/warnings/errors, then deliberately cut 1.0.0). required_version mapped any MAJOR/breaking bump to {major+1}.0.0 unconditionally. Fix: when previous major==0, a breaking change bumps the MINOR (0.y -> 0.(y+1)); only at >=1.0.0 does breaking bump the major. Fixed + tested (test_breaking_change_in_0x_bumps_minor_not_to_1_0_0); repo re-stamped 0.10.0 -> 0.11.0.