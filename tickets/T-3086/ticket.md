---
id: T-3086
title: 'Break the 182-node import cycle (redo): T-3064 closed done without performing
  the extraction'
state: in-progress
kind: feature
origin: human
created: '2026-08-27'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_models.py
- src/frob/findings.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: set
  reason: Carry the real extraction work that T-3064 was closed done without performing;
    record the evidence and that its blocker T-3066 has landed
  actor: logan
  at: '2026-08-27'
  old_length: 0
  new_length: 3464
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-3064 is recorded as DONE but the extraction was never performed. This ticket
carries the actual work.

WHAT ACTUALLY HAPPENED. T-3064's own done-report opens:

    "T-3064 is BLOCKED, not implemented. The extraction was not performed
     against my own judgement to hand-edit imports."
    "No code change to verify with tests -- nothing outside `tickets/` was
     touched."

and its land commit `9d78e63b5` contains only CHANGELOG.md, changelog.d/,
rapid-debt.jsonl and files under tickets/. Zero source changes. The ledger
nonetheless shows `T-3064 [done]`, and it still carries
`blocked_by=['T-3066']`. The 182-node import SCC is NOT broken.

THE AGENT DID THE RIGHT THING and this ticket must not be read as a criticism
of it. It ran the real verb:

    frob refactor split frob.gates._models \
      --symbols Severity,WaiverRef,DebtEntry,Violation \
      --into frob.gates._findings

which refused at the `import_resolution` stage with roughly 40 false
"semicolon-joined" findings. It refused to hand-edit imports as a workaround
(correct -- that is a standing directive), traced the root cause to
`ast.walk` in `_shares_line_with_sibling_statement()`, and filed T-3066. The
defect is that the LEDGER let this close as done; that is filed separately.

THE BLOCKER IS NOW GONE. T-3066 landed at `7a02dfee2` with a real fix to
`src/frob/refactor/_scan.py` (+57) and 101 lines of new tests. So the verb
should now perform this extraction. VERIFY THAT FIRST, before anything else --
run the split command above and confirm it no longer false-refuses. If it
still refuses, STOP and report; do not fall back to hand-editing imports.

THE CUT (unchanged from T-3064, re-verify the numbers before relying on them):
`src/frob/gates/_models.py` is 352 lines with 98 importers across 9 packages.
It mixes UNIVERSAL VALUE TYPES (`Severity`, `Violation`, `WaiverRef`,
`DebtEntry`, arguably `DeprecatedEntry`) with GATE MACHINERY (`GateStats`,
`GateReport`, `GateConfig`, `PreworkSweep`, `SystemSpec`). Twenty-one
importers OUTSIDE `gates` reach in purely for a value type, which forces
layer-3 analysis code (`vet`, `perf`, `dup`, `fuzz`, `policy`) to depend on
layer-4 checking code. Extract the value types to a leaf module that imports
nothing from frob but primitives; `gates/_models.py` keeps the machinery and
imports the leaf.

ONE CUT, THEN RE-MEASURE. Do not try to plan the whole decomposition from the
182-node list. Make this cut, re-run `frob cycle`, and let the new output name
the next one -- file that as a sibling rather than doing it here. Report the
SCC node count before and after. A smaller-than-hoped reduction is a useful
measurement, not a failure.

DO NOT chase `gates/_flag_coverage.py:261`'s function-local `frob.app` import.
A deferred import inside a function body creates no import-time edge, so
"fixing" it would feel productive and change nothing measurable.

ACCEPTANCE
- The extraction is performed with `frob refactor`, not hand-edited imports.
  State the exact command run.
- The universal value types live in a leaf module importing nothing from frob
  but primitives; the 21 non-gates importers import the leaf.
- `frob cycle` SCC node count reported BEFORE and AFTER.
- No behaviour change; existing tests pass unchanged.
- The next cut is filed as a sibling ticket, named from the re-measured cycle.
- If `frob refactor split` still false-refuses after T-3066, report that as the
  finding and stop -- do not work around it.
