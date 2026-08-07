---
id: T-1016
title: 'DOC006 doc-pointer burn-down round 2: remainder (~131 findings, fragmented)'
state: done
kind: bug
origin: agent
created: '2026-07-27'
priority: low
parent: null
tier: ticket
sprint: null
scope:
- docs/**
- src/frob/gates/_docptr.py
- tests/test_docptr_gate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_docptr_gate.py::TestDoc006Config::test_all_caps_citation_tag_not_flagged
- tests/test_docptr_gate.py::TestDoc006Config::test_declared_but_unset_section_not_flagged
- tests/test_docptr_gate.py::TestDoc006Symbol::test_reexported_class_attribute_chain_not_flagged
- tests/test_docptr_gate.py::TestDoc006Symbol::test_dunder_init_mid_chain_resolves_to_module
designated_repro_test: null
threat: null
component: null
---
Follow-up to T-1015 (DOC006 doc-pointer burn-down, round 1): after
matcher hardening (directory-prefix + suffix FILE/PATH resolution,
enumeration-list/domain-citation shape rejection, multi-manifest CONFIG
REFERENCE resolution against pyproject.toml/Cargo.toml, `.git/`-path
exemption, and a tickets-archive.md verbatim-ledger exclusion) plus a
handful of targeted illustrative-example waivers, DOC006 findings measured
771 -> 131 (see T-1015's Done report for the full before/after
cluster table).

The remaining 131 findings are fragmented across ~30 doc files with no
single dominant cluster left (round-1's own measurement, `--only docblocks
--json`, 62 config reference / 30 file/path / 20 code symbol / 13
doc-anchor link / 9 cli invocation). Largest remaining single files:
docs/modules/vet.md (16), docs/modules/gates.md (12), docs/modules/perf.md
(8), CHANGELOG.md (7), docs/strata/threat.md (6). Work this ticket by:

1. Re-measure with a fresh chunked `frob check --only docblocks --json`
   (counts may have drifted since round 1).
2. For each remaining finding, determine per-file/per-line whether it is:
   - a genuinely stale doc pointer (fix the doc prose to the current
     path/symbol/config key), or
   - a further matcher false-positive class worth generalizing (check for
     new clusters before assuming everything left is genuine drift), or
   - a genuinely external/illustrative pointer (a nearby `frob:waive
     DOC006 reason="..."`).
3. Re-check promotion (WARN -> ERROR) once the live count is near zero;
   record the decision with count evidence in docs/audits/gates-quality.md
   under the DOC006 section T-1015 added.

Scope: docs/**, src/frob/gates/_docptr.py, tests/test_docptr_gate.py.
Origin: agent (T-1015 round-1 remainder).