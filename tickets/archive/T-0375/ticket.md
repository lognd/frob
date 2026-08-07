---
id: T-0375
title: frob-dup and frob-arch stage summaries must be waiver-aware (report waived
  separately, like gates)
state: done
kind: bug
origin: human
created: '2026-07-20'
priority: medium
parent: T-0204
tier: ticket
sprint: null
scope:
- src/frob/app/
- src/frob/dup/
- src/frob/arch/
- src/frob/gates/
- src/frob/check/
- docs/modules/dup.md
- docs/modules/arch.md
- docs/modules/gates.md
- tests/unit/test_check.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_check.py::TestDupArchWaiverAwareSummaries::test_dup001_waived_group_excluded_from_headline_but_listed
- tests/unit/test_check.py::TestDupArchWaiverAwareSummaries::test_dup001_unwaived_group_still_counts
- tests/unit/test_check.py::TestDupArchWaiverAwareSummaries::test_arch001_waived_long_function_excluded_from_headline_but_listed
- tests/unit/test_check.py::TestDupArchWaiverAwareSummaries::test_arch001_unwaived_long_function_still_counts
- tests/unit/test_check.py::TestDupArchWaiverAwareSummaries::test_dup001_partial_group_waiver_does_not_hide_whole_group
- tests/unit/test_check.py::TestDupArchWaiverAwareSummaries::test_dup001_waiver_on_shared_symbol_does_not_hide_distinct_superset_group
- tests/unit/test_check.py::TestDupArchWaiverAwareSummaries::test_dup001_waiving_every_fragment_of_superset_group_waives_it_too
designated_repro_test: null
threat: null
component: null
---
The top-line frob check warning count (131) is inflated by findings already accounted for via reasoned frob:waive. Breakdown: 127 frob-dup groups (10 carry reasoned DUP001 waivers from T-0364 but are STILL counted) + 3 frob-arch warnings (waived ARCH001 long-functions from T-0361, STILL counted) + 1 gates warning. The GATES stage does the right thing: it reports 0 errors, 1 warning, 128 WAIVED -- separating accounted findings from the headline. The frob-dup and frob-arch STAGE summaries do NOT: they report raw scan counts with no waiver subtraction, so a group a developer HAS honestly dispositioned with a written reason still counts against the zero-warnings headline. This makes reason-waiving pointless for the metric and contradicts the T-0204 honest-summary-line goal. Fix: make the frob-dup and frob-arch stage summaries waiver-aware -- cross-reference DUP001/DUP002 and ARCH001 waive edges and report N groups (M waived, K unaccounted) with the headline = unaccounted only, mirroring gates. Do NOT hide waived findings; list them under a waived section like gates does. Add tests: a group with a DUP001 waiver is excluded from the unaccounted headline but still listed as waived; an unwaived group still counts.