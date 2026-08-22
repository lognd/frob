## Done report

CONFIRMED via `frob check --stamp-baseline`/direct measurement: `gate:PERF`'s
`perf_gate` (`src/frob/gates/__init__.py`) reported `Violation.file` as an
ABSOLUTE path -- `frob.perf.perf_rules`'s per-symbol violations inherit it
straight from `ParsedFile.path`, itself `str(parse_file(root / rel_path))`'s
absolute result; `ratchet_violations`'s PERF009 does the same via
`str(root / ".frob" / ...)`. Every other gate, and the graph's own
`frob:waive` edges (`src/a.py::scan` style), use a repo-relative path.
`frob.gates._waive._match_waiver`'s file-level fallback does exact string
equality (`waiver_file == violation.file`) -- an absolute violation.file can
never equal a relative waiver src, so every `frob:waive PERF00x` directive
in the tree was silently inert. Proved this directly with an isolated
`tempfile.TemporaryDirectory()` repro (perf_gate + build_graph + _apply_
waivers, no CLI/cache involved) before touching any code, then confirmed the
SAME defect against the real, already-existing waiver at
`src/frob/app/ticket_runner/_rapid_sweep.py:1652`.

FIX: `perf_gate` now relativizes every violation's `.file` to repo-relative
(`_relativize_perf_violation_file`, `src/frob/gates/__init__.py`) at its own
return boundary -- the one place both producers (`perf_rules`,
`ratchet_violations`) funnel through before `_apply_waivers` ever sees the
result. Left `ParsedFile.path`/`perf_rules`'s internal disk I/O
(`_source_lines`) untouched -- those still need a real, resolvable absolute
path; only the FINAL violation object reported out of `perf_gate` is
relativized, so the file/line the message names now matches what a human or
another gate would report too.

Did NOT need the ticket's fallback option (make `frob check` refuse a
`frob:waive` naming a rule the gate cannot honour) -- confirmed the gate
COULD honour waivers all along, this was a plain path-shape bug in one
function, not a design limitation of a native gate. `gate:PERF`'s Python
producer (`perf_rules`) already goes through the same `_apply_waivers`
spine as every other gate; nothing about it is architecturally unwaivable.

MEASURED IMPACT (acceptance criterion 3): ran `perf_gate` + `_apply_waivers`
against this repo's own full tree, before vs after the fix:
  - Raw findings: 169 (unchanged by the fix -- it's a filtering bug, not a
    detection bug)
  - BEFORE (main): 169 kept, 0 waived -- every single frob:waive PERF00x
    directive in the tree was a no-op
  - AFTER (this fix): 53 kept, 116 waived
So 116 PERF findings were being silently, permanently unwaivable before
this fix -- each one either had to be "fixed" (sometimes by making working
code wrong, as T-2303's own investigation found for 3 sites) or simply
accumulate forever in the floor and keep re-triggering post-land sweep
regression tickets.

POSITIVE CONTROLS (all three from the ticket body, all passing):
1. A waived PERF site produces no finding --
   test_frob_waive_perf004_suppresses_the_named_finding
2. MUST-STILL-PASS: an unwaived genuine PERF site still produces one (not a
   blanket suppression) --
   test_frob_waive_perf004_does_not_blanket_suppress_other_sites
3. The existing waiver at _rapid_sweep.py:1652 stops reporting --
   test_the_preexisting_rapid_sweep_waiver_now_actually_suppresses (run
   against the REAL repo tree, not a tmp fixture)

Plus the designated repro itself --
test_perf_gate_reports_a_repo_relative_file_not_absolute -- which asserts
every perf_gate violation.file is relative; confirmed FAILED_AT_PARENT via
`frob ticket evidence --check-repro` against the test-only commit
(37add098f), split from the fix commit specifically so a real pre-fix
verdict was reachable (the T-2021/T-2025 two-commit technique, since a
squashed land can never retroactively prove a test-without-fix state).

Changed:
- src/frob/gates/__init__.py::perf_gate (relativize violations before
  returning)
- src/frob/gates/__init__.py::_relativize_perf_violation_file (new, private
  helper)
- tests/test_gates.py (4 new tests in TestOptInGates)

Evidence:
- tests/test_gates.py::TestOptInGates::test_perf_gate_reports_a_repo_relative_file_not_absolute
  (designated repro, FAILED_AT_PARENT confirmed)
- tests/test_gates.py::TestOptInGates::test_frob_waive_perf004_suppresses_the_named_finding
- tests/test_gates.py::TestOptInGates::test_frob_waive_perf004_does_not_blanket_suppress_other_sites
- tests/test_gates.py::TestOptInGates::test_the_preexisting_rapid_sweep_waiver_now_actually_suppresses
All 4 pass; full TestOptInGates class (12 tests) passes; targeted
perf-keyword pytest -k run (10 tests) passes.

Filed: none new this round -- T-2303's own three follow-ups (ARCH/PERF
already-covered-by-this-ticket/SELFAUDIT) are filed separately per the
coordinator's own next-series instruction, cross-referencing this ticket
for the PERF piece rather than duplicating it.

Gates: targeted pytest runs above green. Did not run a full unscoped
`frob check` (playbook 3c/6c) -- the 169/53/116 measurement above IS the
direct, decisive measurement the ticket asked for, taken with the same
`perf_gate`/`_apply_waivers` calls the real gate pipeline uses, not
inferred from a CLI wrapper.

### Changed
```
 src/frob/gates/__init__.py |  36 ++++++++++++++-
 tests/test_gates.py        | 106 +++++++++++++++++++++++++++++++++++++++++++++
 tickets/T-2314/ticket.md   |  39 ++++++++++++++++-
 3 files changed, 178 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestOptInGates::test_perf_gate_reports_a_repo_relative_file_not_absolute` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestOptInGates::test_frob_waive_perf004_suppresses_the_named_finding` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestOptInGates::test_frob_waive_perf004_does_not_blanket_suppress_other_sites` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestOptInGates::test_the_preexisting_rapid_sweep_waiver_now_actually_suppresses` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@scripts/fleet_status.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/release/_cli.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/tickets/_land_git_ops.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, DOC001@docs/commands/release.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/gates/_fmt_directives.py, DRIFT002@scripts/fleet_status.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PERF004@src/frob/app/ticket_runner/_new.py, PRE001@tickets/T-2314, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK004@tickets.md
