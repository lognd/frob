## Done report

Verification close: re-measured each of the four T-0204 families from a
full `frob check` run (gates-fast + gates-native + gates-security +
lint + static, natives rebuilt), not from stale prior Done reports.

exports: `frob-exports(pkg)` is an advisory-only tool (exit_code=0
always, "note"-severity diagnostics, never a gate) -- it was never
literally driveable to zero repo-wide. T-0871/T-1167's disposition
scoped 9 specific packages (frob top-level, arch, lang, mutate, perf,
scaffold, serve, testing, vet) and those are confirmed at zero missing
symbols right now. Packages outside that scope (app 6, gates 23, graph
4, process 3, process/parsers 1, strata 5, tickets 29) were never
brought into T-0871/T-1167's scope by the human directive and remain
non-zero -- honest, not a regression, since nothing claimed them fixed.

dup: the enforced rule is the "clones" gate (DUP001/DUP002,
`frob check --only clones`), separate from the legacy advisory
`frob-dup` summary tool (also exit_code=0 always, currently reports 331
groups/1 waived as informational text, not gated). The clones gate
itself measures 0 errors, 0 warnings right now -- T-0861/T-0862's
triage plus the DUP001/DUP002 gate wiring holds.

arch: gate:ARCH measures 0 errors (only warnings, all 59 waived with
reasons) -- ARCH001/101/102/103 promoted to error-tier at zero holds.

perf: gate:PERF measures 0 errors, but 4 UNWAIVED WARNINGS exist right
now that were not present in T-1041's own closing measurement:
PERF005 src/frob/vet/_taint.py:134, PERF008 src/frob/arch/_ffi.py:298,
PERF008 src/frob/serve/_watch.py:169, PERF008 tests/test_serve_watch.py:86.
This is a real regression against T-1041's "zero unwaived" state (new
code added since introduced these). Filed forward per fix-or-file
rather than folded silently into this close: T-1191
("perf: fix 4 unwaived PERF005/PERF008 findings found in T-0204
verification close").

TEST family (T-0875's own burn-down, cited alongside the umbrella's own
four families though not one of the four named in the ticket body):
gate:TEST also shows new unwaived debt beyond T-0875's zero state --
2 new TEST003 (src/frob/tomlio.py, strata-core/src/parse, both added
after T-0875) and 3 new TEST014 ambiguous-`stop`-leaf-name collisions
(StackSampler.stop / CoverageWatcher.stop / WatchThread.stop, all added
after T-0875). TEST006 (no coverage stamp) is an ordinary worktree
artifact, not counted. Filed forward: T-1190
("test: fix 5 unwaived TEST003/TEST014 findings found in T-0204
verification close").

Disposition: exports and dup/clones and arch are each honestly
accounted for exactly as the umbrella's own children (T-0871/T-1167,
T-0861/T-0862, T-0872/T-0873-dropped-with-reason) already recorded --
no regression found in those three. perf and the related TEST warning
family have each accrued new, real, unwaived debt since their own
closing tickets (T-1041, T-0875) -- fixed forward via two newly filed
tickets rather than left silent, per this ticket's own "fix-or-file
first" instruction. Closing T-0204 itself: the umbrella's accounting
work (re-measuring, triaging genuine-vs-informational per family,
filing what regressed) is what this ticket asked for and is complete;
the underlying PERF/TEST debt itself is not re-opened under T-0204 but
tracked under the two new tickets.

### Changed
```
 tickets.md | 98 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++--
 1 file changed, 96 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 0 error(s), 405 warning(s), 678 waived
- error-findings: none (measured, zero errors)
