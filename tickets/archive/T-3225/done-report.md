## Done report

Premise held: tests/test_waive_gate.py::TestWaive006RealRepo::test_zero_errors_on_real_repo
still failed on main with the named WAIVE006 finding. Read the
frob:waive AFFECT001 comment above scan_emitted_rule_ids: its reason
cites two things -- (1) the doc anchor is unaffected by T-3003's
internal-only path-formatting change (a permanent claim), and (2) "its
own lease is held by T-2993", which WAIVE006's T-2622 lease-phrasing
extension correctly reads as a binding claim. T-2993 is done, so (2) is
stale. (1) is still true and does not depend on any ticket's lease
state, so the fix is re-justifying the waiver as permanent rather than
removing it outright -- reworded the reason to drop the now-terminal
T-2993 lease mention and state the doc-unaffected claim as the whole
justification.

Evidence: tests/test_waive_gate.py::TestWaive006RealRepo::test_zero_errors_on_real_repo

Filed: none
