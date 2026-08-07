## Done report

Registered a git merge driver for tickets.md. `frob ticket merge-driver
%O %A %B` (src/frob/__main__.py + app/ticket_runner.py::_merge_driver)
implements git's merge-driver protocol by REUSING the existing
frob.tickets.splice_ledger (no reimplementation): id-level union, newer
state-rank wins, evidence union, archive-aware. .gitattributes routes
`tickets.md merge=frob-ledger`; docs/modules/tickets.md documents the
one-time `git config merge.frob-ledger.driver "frob ticket merge-driver
%O %A %B"` setup and the fail-safe (on splice error it exits 1 leaving %A
byte-identical so git falls back to a normal conflict -- never corrupts the
ledger). Agent-playbook section 10 now leads with driver registration.

Evidence (3 of 5 tests, all pass): the real-git end-to-end test
(registers the driver via actual git config/.gitattributes, merges two
branches that each append a ticket at the same ledger line, asserts a
CLEAN non-conflicted merge with both tickets present -- not mocked), plus
newer-state-wins and the malformed-theirs fail-safe. Reviewer APPROVED
(rigorous on the real-git test and the no-corruption fail-safe).

Coordinator landing note: the driver is now REGISTERED in this shared
checkout (`git config merge.frob-ledger.*` done), so from here on
tickets.md merges auto-splice -- directly ending the ~8x manual splice
friction this ticket's own body records. Scope widened to the CLI-wiring
files the subcommand structurally requires (T-draft-bc39c17f tracks the
scope-declaration gap; filed as T-0446). Landed via 3-way + new-file copy.
