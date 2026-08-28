## Done report

Premise held: tests/test_docptr_gate.py::TestDoc004Doc006ZeroOnFrobsOwnRepo::test_doc004_doc006_zero_against_live_repo
still failed on main with the two DOC006 findings the ticket named
(confirmed both target paths, src/frob/gates/_platform_guards.py and
tests/test_platform_guards_gate.py, are not tracked files -- `git
ls-files` returns nothing for either), and T-2962 (the ticket that
names them) is still queued, so the split those paths describe has not
landed. Fix: added a `frob:waive DOC006 reason="..."` HTML comment
directly above each pointer line in tickets/T-2962/ticket.md, per
DOC006's own documented nearby-line waiver convention
(src/frob/gates/_docptr.py's `_nearby_waived`/`_WAIVE_DOC006_RE`),
stating the paths are the ticket's own illustrative target for a split
not yet landed.

Evidence: tests/test_docptr_gate.py::TestDoc004Doc006ZeroOnFrobsOwnRepo::test_doc004_doc006_zero_against_live_repo
(recorded via --evidence-cmd, exit=0)

Filed: none
