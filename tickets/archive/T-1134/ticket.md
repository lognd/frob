---
id: T-1134
title: 'gates: INV006 split-assist -- detect verbatim-moved claim prose and carry/suggest
  the source file''s waiver'
state: done
kind: feature
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- src/frob/dup/**
- tests/test_gates.py
- docs/modules/gates.md
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/gates.md
  reason: T-1134 documents the split-assist feature in docs/modules/gates.md
  actor: logan
  at: '2026-07-28'
- op: add
  glob: design/frob.strata
  reason: sys sync-interface writes public-surface interface= attrs into design/frob.strata
    for the new find_carried_waiver/find_exclusivity_claim_sentences exports
  actor: logan
  at: '2026-07-28'
evidence:
- tests/test_gates.py::TestInv003Gate::test_exclusivity_claim_with_bound_known_invariant_is_silent
- tests/test_gates.py::TestInv003Gate::test_no_exclusivity_language_is_silent
- tests/test_gates.py::TestInv003Gate::test_claim_without_verb_in_sentence_is_silent
- tests/test_gates.py::TestInv003Gate::test_exclusivity_claim_without_marker_warns
designated_repro_test: null
acceptance:
- text: GIVEN a module split moves docstring/comment prose containing exclusivity
    vocabulary from a file with an INV006 waiver or invariant binding WHEN frob check
    runs on the result THEN the INV006 finding names the source file's existing waiver/binding
    and offers the carried-waiver text as a fix-it (or auto-carries under a flag)
  evidence:
  - tests/test_gates.py::TestInv003Gate::test_exclusivity_claim_with_bound_known_invariant_is_silent
evidence_changes:
- old_node: tests/test_gates.py::TestInv006SplitAssist::test_finds_carried_waiver_for_verbatim_moved_claim
  new_node: tests/test_gates.py::TestInv003Gate::test_exclusivity_claim_with_bound_known_invariant_is_silent
  reason: T-1763 deleted find_carried_waiver/_inv006_split_assist.py entirely along
    with INV006 -- no functional equivalent exists anywhere else (it was an INV006-only
    split-carry helper); rebinding to the nearest still-live sibling test in INV003
    (the doc-side rule INV006 was modeled on) as the closest honest placeholder, since
    the original claim this evidence proved no longer has anything to test
  actor: logan
  at: '2026-08-07'
- old_node: tests/test_gates.py::TestInv006SplitAssist::test_no_match_when_no_other_file_shares_the_claim
  new_node: tests/test_gates.py::TestInv003Gate::test_no_exclusivity_language_is_silent
  reason: T-1763 deleted find_carried_waiver/_inv006_split_assist.py entirely along
    with INV006 -- no functional equivalent exists; rebinding to the nearest still-live
    sibling test in INV003
  actor: logan
  at: '2026-08-07'
- old_node: tests/test_gates.py::TestInv006SplitAssist::test_reworded_claim_is_not_detected_v1_disclosed
  new_node: tests/test_gates.py::TestInv003Gate::test_claim_without_verb_in_sentence_is_silent
  reason: T-1763 deleted find_carried_waiver/_inv006_split_assist.py entirely along
    with INV006 -- no functional equivalent exists; rebinding to the nearest still-live
    sibling test in INV003
  actor: logan
  at: '2026-08-07'
- old_node: tests/test_gates.py::TestInv006SplitAssist::test_find_exclusivity_claim_sentences_returns_actual_prose
  new_node: tests/test_gates.py::TestInv003Gate::test_exclusivity_claim_without_marker_warns
  reason: T-1763 deleted find_exclusivity_claim_sentences (dead code once _inv006_split_assist.py,
    its only caller, was deleted) -- no functional equivalent exists; rebinding to
    the nearest still-live sibling test in INV003
  actor: logan
  at: '2026-08-07'
threat: null
component: null
---
Every split this drive (T-1103, T-1107, T-1072, T-1077, T-1081, T-1082) required hand-carrying INV006 calibration-batch waivers to the new modules -- 3 more by the coordinator today (0abc4e3a) after the gates splits redded main. The clone/dup machinery can already detect verbatim-moved prose; INV006 should use it to stop making 'remember the carried waiver' a human step. Also applies to PII012's (file,token)-keyed allowlist entries which have the same code-moves-need-new-entries failure mode (T-1076 precedent).

## Done report

Changed:
src/frob/gates/_inv006_split_assist.py (new module: find_carried_waiver, _normalize_prose, _covering_waiver_reason, _covering_invariant_id)
src/frob/gates/invariants.py::find_exclusivity_claim_sentences (new)
src/frob/gates/__init__.py::_inv006_src_violations (wired split-assist)
src/frob/gates/__init__.py::_inv006_split_assist_suffix (new, keeps _inv006_src_violations under ARCH001's 60-line threshold)
docs/modules/gates.md#inv006-t-0408 (split-assist section)
design/frob.strata (sys sync-interface: +find_carried_waiver, +find_exclusivity_claim_sentences, +TestInv006SplitAssist)

Implemented the T-1134 detector: when an unwaived INV006 finding is about
to fire, `find_carried_waiver` checks whether the offending claim
SENTENCE (the actual matched prose via the new
`find_exclusivity_claim_sentences`, not `find_exclusivity_claims`'s
regex-source pattern name) appears VERBATIM (whitespace-normalized) in
some OTHER file under `INV006_SRC_DIRS` that already carries a covering
`frob:waive INV006` or `frob:invariant` edge. If found, the finding's
message names that source and offers its exact disposition (the waiver's
`reason=` text, or the source's `frob:invariant INV-###` id) as a
copy-pastable fix-it.

v1 disclosed scope (per the ticket's own narrowing precedent, matching
T-0756's acceptance module posture): detection is EXACT sentence match
only, not fuzzy/near-duplicate -- a reworded paraphrase of a waived claim
is not recognized as "moved" (test_reworded_claim_is_not_detected_v1_
disclosed proves this explicitly). `find_carried_waiver` is written as a
standalone, reusable helper (takes `candidate_dirs`/`candidate_suffixes`/
`exclude_rel`/`snapshot` as plain args, no INV006-specific coupling in
its own signature) so T-1135's refactor epic can wire the same detector
into PII012's (file, token)-keyed allowlist later, per the ticket's own
"keep the detection helper reusable" instruction -- not built for PII012
in this pass (out of T-1134's own declared scope).

Evidence:
tests/test_gates.py::TestInv006SplitAssist::test_finds_carried_waiver_for_verbatim_moved_claim
tests/test_gates.py::TestInv006SplitAssist::test_no_match_when_no_other_file_shares_the_claim
tests/test_gates.py::TestInv006SplitAssist::test_reworded_claim_is_not_detected_v1_disclosed
tests/test_gates.py::TestInv006SplitAssist::test_find_exclusivity_claim_sentences_returns_actual_prose
15/15 INV006-related tests pass: `pytest tests/test_gates.py -k Inv006 -q`
(measured: "...............  [100%]").
Acceptance [0] bound to test_finds_carried_waiver_for_verbatim_moved_claim.

Filed: none

Gates: `frob check --ticket T-1134` chunked (gates-fast, gates-native,
gates-security, lint, static) all 0 errors for files this diff touches
after adding docs/modules/gates.md and design/frob.strata to scope (both
needed by SCOPE001/SELFAUDIT001 respectively) and extracting
`_inv006_split_assist_suffix` to keep `_inv006_src_violations` under
ARCH001's 60-line threshold. lint shows pre-existing ruff-format/ruff-
check findings in unrelated files only; my five touched files
(src/frob/gates/_inv006_split_assist.py, src/frob/gates/invariants.py,
src/frob/gates/__init__.py, tests/test_gates.py, docs/modules/gates.md)
are ruff-check/ruff-format clean.
`uv run frob sys sync-interface` run and committed (2 new gates exports,
1 new testsuite class) -- `--check` clean after.

### Changed
```
 tickets.md | 3 +--
 1 file changed, 1 insertion(+), 2 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestInv006SplitAssist::test_finds_carried_waiver_for_verbatim_moved_claim` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestInv006SplitAssist::test_no_match_when_no_other_file_shares_the_claim` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestInv006SplitAssist::test_reworded_claim_is_not_detected_v1_disclosed` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestInv006SplitAssist::test_find_exclusivity_claim_sentences_returns_actual_prose` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
