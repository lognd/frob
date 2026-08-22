---
id: T-2438
title: a symbol-bound frob:waive silently fails to match when symrefs differ, with
  no fallback and no diagnostic
state: done
kind: bug
origin: human
created: '2026-08-18'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_waive.py
evidence_scope:
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/test_gates.py::TestTestGate::test_match_waiver_symref_formatting_difference_still_waives
- tests/test_gates.py::TestTestGate::test_match_waiver_logs_diagnostic_on_genuine_symref_mismatch
- tests/test_gates.py::TestTestGate::test_match_waiver_different_symbol_same_file_still_not_waived
designated_repro_test: tests/test_gates.py::TestTestGate::test_match_waiver_symref_formatting_difference_still_waives
acceptance:
- text: Given a symbol-bound frob:waive whose symref differs from the violation's
    symref only in formatting, when the gate runs, then the finding is waived rather
    than silently kept.
  evidence:
  - tests/test_gates.py::TestTestGate::test_match_waiver_symref_formatting_difference_still_waives
- text: Given a symref-carrying violation with no matching symbol-exact waiver but
    a same-file same-rule waiver present, when matching fails, then a diagnostic names
    both strings rather than returning None silently.
  evidence:
  - tests/test_gates.py::TestTestGate::test_match_waiver_logs_diagnostic_on_genuine_symref_mismatch
- text: Given a waiver bound to a DIFFERENT symbol in the same file, when an unrelated
    finding is checked, then it is still kept, proving precision was not traded for
    a blanket file waiver.
  evidence:
  - tests/test_gates.py::TestTestGate::test_match_waiver_different_symbol_same_file_still_not_waived
threat: null
component: gates
anchor: false
anchor_reason: null
land_commit: c9bd75d69c294b9b8367c47ad96413b7cb19a9ad
---
A `frob:waive` directive bound to a SYMBOL can be permanently inert with
no diagnostic. Reported live by Series AB: an inline `frob:waive DUP001`
on a method symbol did not suppress its `gate:DUP` finding even though
the WAIVE edge was confirmed correctly shaped. AB worked around it by
eliminating the duplication rather than relying on the waiver -- so the
directive is still sitting in the tree today, reading as honoured while
doing nothing.

MECHANISM, read from `src/frob/gates/_waive.py::_match_waiver` (lines
~1888-1930). The matcher is ASYMMETRIC:

    if violation.symref is not None:
        for waiver in candidates:
            if waiver.src == violation.symref and _ceiling_ok(...):
                return waiver
        return None            # <-- NO file-level fallback
    # ... only when symref is None do the file-scoped and
    #     package-prefix branches run

So when a violation carries a symref, the ONLY way to waive it is an
exact string match on that symref. Any difference in how the two sides
spell the symbol -- qualified vs bare (`file::Class.method` vs
`file::method`), a decorator/overload variant, a nested class path, a
renamed symbol whose waiver was not updated -- yields a silent
non-match. The `return None` is unconditional: it does not fall back to
the file-scoped branch that would otherwise have matched, and nothing
is logged to say a same-file waiver for the same rule was considered
and rejected.

WHY THIS IS THE HIGH-COST FAILURE MODE. A silently-ignored directive
reads as honoured to anyone grepping for it, so it is invisible in
review and invisible in the gate output. This repo has already paid for
exactly this once: T-2314 found 116 `frob:waive PERF00x` directives that
could never match because one producer emitted absolute paths against
relative waiver edges (169 findings, 0 waived before the fix, 116 after).
That was path shape; this is symbol shape. Same class, same silence.
See also T-2400's cry-wolf dynamic: mechanisms that are wrong in the
quiet direction erode trust in the whole directive DSL.

WHAT TO DETERMINE FIRST (do not assume my reading is the whole story):
  1. Reproduce AB's case. Find the DUP001 finding and the waiver it
     should have matched, and PRINT BOTH STRINGS -- `violation.symref`
     and `waiver.src` -- side by side. Do not theorise about the logic
     before seeing the two values, which is the standing rule for every
     match-should-have-fired bug in this repo.
  2. Establish whether the symref mismatch is a FORMATTING difference
     (the two sides spell the same symbol differently) or a BINDING
     difference (the directive genuinely attached to a different symbol
     than the finding). The fix differs completely.

FIX SHAPE, once (2) is answered:
  - If formatting: normalise at the producer boundary, exactly as T-2314
    did with `_relativize_perf_violation_file` -- one normalisation at
    the point of production, not two consumers taught both spellings.
  - Regardless: a symref-carrying violation that finds no symbol-exact
    waiver, but DOES have a same-file same-rule waiver present, must not
    silently return None. Either fall back to the file-scoped branch or
    emit a diagnostic naming both strings. An inert directive must be
    loud (epic T-2391) -- this is the doctrine applied to the waiver
    layer.
  - Consider a sweep for OTHER currently-inert symbol-bound waivers
    across the tree, the way T-2314 quantified 116. The count is the
    finding; report it even if it is zero, and say what you scanned.

POSITIVE CONTROLS, both directions, mandatory:
  - must-now-waive: a symbol-bound waiver whose symref differs only in
    the formatting identified in (2) must suppress its finding.
  - must-still-keep: a waiver for a DIFFERENT symbol in the same file
    must NOT suppress an unrelated finding. Do not fix this by making
    every same-file waiver match everything -- that would turn a precise
    mechanism into a blanket file waiver and delete the precision
    T-2338 deliberately built (nearest-line attribution for display).