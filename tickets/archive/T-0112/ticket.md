---
id: T-0112
title: 'threat B: capability->obligation instantiation + THREAT002 precondition completeness'
state: done
kind: security
origin: human
created: '2026-07-17'
priority: medium
blocked_by:
- T-0111
parent: T-0109
tier: ticket
sprint: null
scope:
- docs/strata/**
- src/frob/strata/**
- strata-core/**
- tests/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_threat.py::TestBenignCapability::test_empty_reason_is_rejected
- tests/unit/strata/test_threat.py::TestCapabilityCompleteness::test_known_capability_kind_is_classified
- tests/unit/strata/test_threat.py::TestCapabilityCompleteness::test_unknown_capability_kind_is_a_violation
- tests/unit/strata/test_threat.py::TestCapabilityCompleteness::test_benign_capability_excuses_an_unknown_kind
- tests/unit/strata/test_threat.py::TestCapabilityCompleteness::test_kind_scoped_may_atom_is_still_classified
- tests/unit/strata/test_threat.py::TestCapabilityCompleteness::test_no_capabilities_no_violations
- tests/unit/strata/test_threat.py::TestCapabilityCompleteness::test_multiple_unknown_kinds_each_violate
- tests/unit/strata/test_threat.py::TestCapabilityCompleteness::test_non_default_catalog_moves_the_taxonomy_with_it
- tests/unit/strata/test_threat.py::TestCapabilityCompleteness::test_thin_catalog_shrinks_the_taxonomy_with_it
- tests/unit/strata/test_threat.py::TestEvaluateThreats::test_unclassified_capability_reports_threat002
- tests/unit/strata/test_threat.py::TestEvaluateThreats::test_benign_capability_param_excuses_threat002
designated_repro_test: null
acceptance:
- text: GIVEN capability client_storage WHEN CWE-922 undischarged THEN it fires; GIVEN
    an unclassified sink THEN THREAT002 errors
  evidence: []
threat: elevation-of-privilege
component: null
---
capabilities drag in weakness obligations (html_render->79/116, sql->89, client_storage->922/312, exec->78, deserialize->502, fetch_url->918); sink taxonomy; THREAT002 unclassified-sink deny-by-default error. threat.md phase B.