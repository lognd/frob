## Done report

Corrected section 0 of docs/modules/dup-sota-survey.md (and the matching
item-26 cross-reference): the stale "DUP001/DUP002 are pure rule functions
but NOT wired into frob.gates.__init__" claim is replaced with the actual
state -- dup_gate (T-0191) wires DUP001/DUP002 via the real find_clones
pipeline, registered as the opt-in "clones" gate, off by default and turned
on by [dup].enforce=true, silent when off or when frob-core is absent. The
correction is honestly nuanced: default-off enforcement means most ADOPT
verdicts still lack teeth until a repo opts in. Verified against
src/frob/gates/__init__.py (dup_gate registered as "clones" at line ~3711)
before rewording.

Evidence: tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
(docs-only change; cites the existing CLI-dispatch integration test per the
agent-playbook T-0167 precedent rather than inventing a docs test). Landed
surgically onto current main; docs-only, no conflict.
