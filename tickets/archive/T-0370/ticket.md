---
id: T-0370
title: 'arch: abstraction-opportunity residue -- require body-similarity or signature-specificity,
  not bare shared signature'
state: done
kind: bug
origin: human
created: '2026-07-20'
priority: medium
parent: T-0204
tier: ticket
sprint: null
scope:
- src/frob/arch/
- src/frob/dup/
- tests/unit/test_arch.py
- docs/modules/arch.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_arch.py::TestAbstractionOpportunityDiscriminators::test_generic_signature_unrelated_bodies_not_flagged
- tests/unit/test_arch.py::TestAbstractionOpportunityDiscriminators::test_generic_signature_near_duplicate_bodies_still_flagged
- tests/unit/test_arch.py::TestAbstractionOpportunityDiscriminators::test_specific_signature_genuine_family_still_flagged
- tests/unit/test_arch.py::TestAbstractionOpportunityDiscriminators::test_generic_signature_only_two_bodies_similar_reports_pair
- tests/unit/test_arch.py::TestDispatchFamilySuppression::test_accidental_same_signature_still_flagged
- tests/unit/test_arch.py::TestDispatchFamilySuppression::test_init_reexport_does_not_suppress
- tests/unit/test_arch.py::TestDispatchFamilySuppression::test_test_file_co_mention_does_not_suppress
designated_repro_test: null
threat: null
component: null
---
After T-0360 (dispatch-family suppression), 67 abstraction-opportunity findings remain on src. MANY are coincidental collisions on over-generic signatures (30+ unrelated predicates all typed (str)->bool; heterogeneous helpers all (str)->str). A shared GENERIC signature across semantically-unrelated functions is NOT an extractable abstraction -- you cannot factor 30 unrelated boolean predicates into one helper just because they take a str. A GENUINE opportunity needs either (a) a specific/non-generic shared signature, or (b) structurally-similar BODIES (near-duplicate logic -- which is what actually indicates shared extractable code; reuse the dup fingerprinting in src/frob/dup/). Refine _check_abstraction_opportunities to require signature-specificity OR body-similarity before flagging, so the residue drops to only TRUE opportunities. Add tests: unrelated-bodies same-generic-sig group NOT flagged; similar-bodies group STILL flagged. NO threshold loosening that would hide real near-duplicate families. Acceptance: abstraction-opportunity count reflects only genuine extractable families; honest summary.