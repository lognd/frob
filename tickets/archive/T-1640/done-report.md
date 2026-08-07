## Done report

INV006's claim scan ran over a source file's whole raw text, including
every directive's `reason="..."` attribute string -- so a `frob:waive
EXHAUST002 reason="int(str) can only ever raise ValueError, never
TypeError"` justification tripped INV006 on its own (the live incident:
that sentence genuinely uses "only"/"never"), demanding an unrelated
`frob:invariant` binding for a sentence that ARGUES why a different
finding does not apply, not a specification of this file's behavior.
Read the wrong way, the gate rewards a vaguer reason (the cheapest way
to dodge it) over a precise one -- the wrong direction for the waiver
audit (T-1614).

Decision made per the ticket's own framing: NO, a waiver reason (or any
directive's `reason=` attribute value) does not count as a normative
claim for INV006's purposes.

Fix: `_strip_directive_reason_prose` (src/frob/gates/_inv.py) removes
every `reason="..."` directive-attribute span (any verb, not just
`frob:waive`; DOTALL so a folded, backslash-continued multi-line reason
is stripped as one span) from the text INV006's source-side scan
(`_inv006_src_violations`) passes to `find_exclusivity_claims`. Scoped
narrowly to INV006's source scan only -- INV003/INV004's doc-side scans
are unchanged, since the ticket's own incident and this drive's scope
are both source-file-specific.

Two regression tests pin the decision: a waiver reason containing
exclusivity vocabulary no longer fires INV006 (verified to fail without
the fix by reverting it locally and re-running); a genuine claim living
outside any `reason=` span in the same file still fires normally, so the
strip cannot be used to smuggle a real, unwaived claim past the gate.

docs/modules/gates.md's INV006 section documents the decision and its
scope.

Not addressed (explicitly out of scope, noted per the ticket's closing
suggestion): the shared "this span is explanatory text, not a
declaration" abstraction the ticket floats across TICK006/live-tracker/
INV006 was not built -- this fix is INV006-local, matching the other two
detectors' own independent fixes rather than generalizing three
different scanners' notion of prose into one shared primitive in the
same change.

### Changed
```
 tickets.md | 3 +--
 1 file changed, 1 insertion(+), 2 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 0 error(s), 6217 warning(s), 715 waived
- error-findings: none (measured, zero errors)
