---
id: T-2507
title: vet resolves identities then compares them by substring; LEXCHECK001 trigger
  set misses the in operator
state: done
kind: bug
origin: human
created: '2026-08-18'
priority: high
parent: T-2501
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/vet/_capability_core.py
- src/frob/gates/_lexical_selfcheck.py
- tests/test_vet.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_vet.py
  reason: T-2507 deliverable-1 fix's own tests live here (SCOPE001/SCOPE002)
  actor: logan
  at: '2026-08-18'
evidence:
- tests/test_vet.py::TestNeedleMatchesResolvedTokenBoundary::test_module_prefix_matches_with_and_without_trailing_dot
- tests/test_vet.py::TestNeedleMatchesResolvedTokenBoundary::test_call_target_matches_with_and_without_trailing_paren
- tests/test_vet.py::TestNeedleMatchesResolvedTokenBoundary::test_bare_identifier_matches_with_and_without_trailing_paren
- tests/test_vet.py::TestNeedleMatchesResolvedTokenBoundary::test_family_prefix_still_reaches_sibling_family
- tests/test_vet.py::TestNeedleMatchesResolvedTokenBoundary::test_no_false_positive_on_module_name_substring
- tests/test_vet.py::TestNeedleMatchesResolvedTokenBoundary::test_no_false_positive_on_call_target_substring
- tests/test_vet.py::TestNeedleMatchesResolvedTokenBoundary::test_no_false_positive_on_bare_identifier_substring
- tests/test_vet.py::TestNeedleMatchesResolvedTokenBoundary::test_module_prefix_does_not_match_unrelated_leading_segment
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 458712eb3292d77741ee3cf511abab004354554d
---
MEASURED 2026-08-18. frob.vet is NOT naive grepping -- _capability_scan.py
imports parse_file, raw_tree and CallGraph, so call sites really are
parsed and resolved to dotted targets. The problem is that resolution is
then THROWN AWAY at the comparison:

    src/frob/vet/_capability_core.py::_needle_matches_resolved
    return needle in resolved or needle in f"{resolved}("

"in" is substring containment against a resolved name. It is wrong in
both directions at token boundaries: needle "net" matches a resolved
netrc or network_helper; needle "os.system(" matches myos.system(. The
tell is in the needle format itself -- "subprocess.", "os.system(" --
that trailing punctuation is a hand-rolled boundary approximation, which
is exactly what comparing real tokens gives you for free.

There is also an acknowledged raw-text path
(_needle_hits_outside_comments), mitigated by comment-span exclusion
rather than by parsing, and _has_write_mode_open_call(raw, comment_spans)
operates on raw text.

Standing user directive: checks must parse and compare SYMBOLS, never
substring/regex -- a lexical match is wrong in both directions (comments
match, aliases do not).

DELIVERABLE 1: compare resolved identities as dotted-segment sequences
with boundary equality, not containment. The needles' trailing
punctuation then becomes redundant and can be dropped -- that removal is
a falsifiable check that the fix is real rather than cosmetic.

DELIVERABLE 2 (the harder one): LEXCHECK001 currently reports ZERO
findings, and its own docstring describes this exact failure mode. T-2466
widened it after T-2457 shipped a bytes.find substring matcher in this
very file that escaped on BOTH axes (wrong package, wrong trigger). The
widened trigger set is re.search/match/fullmatch/findall/finditer plus
".find(". It does NOT include the "in" operator -- so
"needle in resolved", in the same file that motivated the widening, sits
one operator outside the net. The gate's own words: "A meta-check
narrower than the class of code it polices manufactures FALSE COVERAGE."
Its green result means "no detector matches lexically VIA THE SCANNED
TRIGGER SET", not "no detector matches lexically".

Widening the trigger to "in" needs care -- it is ubiquitous and a naive
trigger would drown the gate. It should fire only on containment tests
whose right-hand side is a RESOLVED / symref-derived value, which means
this needs the same provenance notion as T-2504's confinement lattice.
That is why both are children of T-2501: they should share machinery
rather than grow two answers to "where did this value come from".

POSITIVE CONTROL, BOTH DIRECTIONS, MANDATORY for deliverable 2: a planted
"needle in resolved" must FIRE, and ordinary membership tests
(x in some_set, key in dict) must NOT. Without the must-not-fire half
there is no evidence the trigger is usable rather than merely loud.

Note for whoever picks this up: T-2469 cleared 5 LEXCHECK001 findings in
vet/_supplychain.py on 2026-08-18 by rewriting it onto real parsers. That
makes the package LOOK finished while the core matcher above was never
touched. Do not read that ticket's success as coverage.