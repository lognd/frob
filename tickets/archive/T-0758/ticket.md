---
id: T-0758
title: 'REL201 proof anchoring: check the endpoint with bound code (dst/both), not
  only flow.src -- the one real network flow is silent today'
state: done
kind: bug
origin: agent
created: '2026-07-22'
priority: high
parent: T-0640
tier: ticket
sprint: null
scope:
- src/frob/strata/_reliability.py
- tests/unit/strata/
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_reliability.py::TestUnprovenTimeout::test_codeless_src_with_coded_dst_proves_against_dst
- tests/unit/strata/test_reliability.py::TestUnprovenTimeout::test_codeless_src_with_coded_dst_lacking_evidence_fires_against_dst
- tests/unit/strata/test_reliability.py::TestUnprovenTimeout::test_declared_timeout_with_no_code_evidence_fires
- tests/unit/strata/test_reliability.py::TestUnprovenTimeout::test_declared_timeout_with_real_code_evidence_discharges
- tests/unit/strata/test_reliability.py::TestUnprovenTimeout::test_declared_timeout_with_no_bound_code_is_uncheckable_not_a_violation
designated_repro_test: null
acceptance:
- text: GIVEN f_registry_fetch (foreign src, real timeout=code in the vet caller)
    WHEN REL201 runs THEN it proves against the endpoint with bound code and reports
    PROVED, not uncheckable-silent; a src-codeless dst-coded litmus fixture asserts
    it
  evidence:
  - tests/unit/strata/test_reliability.py::TestUnprovenTimeout::test_codeless_src_with_coded_dst_proves_against_dst
threat: null
component: null
---
Found by T-0640s reviewer: REL201 (timeout proof-against-code) anchors its bind_code proof on flow.src. For the repos ONLY real network flow, f_registry_fetch : registry -> vet, src is the FOREIGN registry node (no bound code), so REL201 is uncheckable-silent there -- while the actual CALLER, vet, has genuinely provable code (src/frob/vet/_registry.py:191, urlopen(url, timeout=timeout_s)). So the one flow this whole family was built to protect is never proof-checked. Fix: REL201 should anchor proof on the endpoint(s) that have bound code -- check the DESTINATION (or both endpoints), not only src -- turning f_registry_fetch from uncheckable-silent into a real PROVED. Add a litmus fixture where src has no code but dst does, asserting the proof runs against dst.