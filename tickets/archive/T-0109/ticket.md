---
id: T-0109
title: 'strata obligation catalog: CWE/CVE + quality anti-pattern auditing (epic)'
state: done
kind: security
origin: human
created: '2026-07-17'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- docs/strata/**
- src/frob/strata/**
- strata-core/**
- src/frob/vet/**
- tests/**
- design/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_litmus_audit_vuln.py::TestAuditVulnGolden::test_fires_undischarged_in_security_and_quality
- tests/unit/strata/test_threat.py::TestCatalogCompleteness::test_missing_entry_is_a_violation
designated_repro_test: null
threat: null
component: null
---
Umbrella: make it impossible to forget a class of protection. CWE weaknesses + performance/reliability/compat anti-patterns as conditional obligations (precondition pattern fires -> cited mitigation discharges -> exhaustiveness proof over a cited baseline). Charter: docs/strata/threat.md. Reuses closure/boundaries/policy/lattice/evidence-ladder; no kernel primitive. CVE joins vet via shared CWE id. Catalog ingested from MITRE CWE + NVD, pinned + digest-verified, never hand-transcribed.
## Done report

Threat-catalog epic closed on completion of all seven children:
T-0111 (std.cwe phase A + THREAT001/003), T-0112 (THREAT002
capability completeness, structurally single-source), T-0113
(sink-effect joins + mitigation-kind chokepoints), T-0110 (CVE->CWE
ingestion + containment report with four honest states), T-0114
(quality anti-pattern families), T-0115 (frob sys audit exhaustiveness
conjunction + vuln/hardened litmus pair), T-0116 (std.compliance six
regulations + privacy-policy reverse audit). The charter's three-part
exhaustiveness proof is checkable end-to-end from .strata source.
Verified at close: full suite green, frob check exit 0.