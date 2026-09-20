## Done report

WHAT: this ticket is a decision record, not code. It raised the semantic hole in
the module-system proposal -- a flow A->B forces A to import B, so a reverse flow
B->A would force the import cycle D-M2 forbids, and 16 of the 11-module
partition's pairs are mutually bidirectional (STRATA-MODULES.md section 2,
computed from the 117 flow declarations).

WHY IT IS DONE: the owner ruled on 2026-09-19 19:30 and the ruling is recorded
verbatim in the body -- HIERARCHY (modules declare their position; platform top,
app and test bottom), IMPORT UP ONLY (importing a module below you is a compile
error naming both modules, so cycles are impossible by construction and the SCC
check becomes a redundant assertion), FLOWS DECLARED BY THE LOWER MODULE in
either direction (only it can name both ends), ACCEPT DOWN (the upper module
declares `accepts f from <lower-module>` by reference, with no import; an
accepts naming a module above is an error). The 16 bidirectional pairs are not
waivers: each migration leaf decides which module is lower and moves the flow
declarations there.

WHERE THE BEHAVIOUR LANDS: no file changes belong to this ticket. The grammar
leaf T-5125 gained two acceptance criteria (the hierarchy declaration
form; `accepts` takes a module reference, never an import alias). The linker
leaf T-5087 gained four (upward-only import check naming both modules,
accepts-direction check, the SCC assertion that must never fire, flows declared
by the lower module). The story T-5081's body now carries the
top-down order of the 11 modules. Both leaves are unblocked from this ticket.

NO BEHAVIOUR CHANGE: nothing executable changed under this id.

### Changed
(no changed files detected)

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
