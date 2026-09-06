---
id: T-4000
title: 'F-215: evidence-cmd records an empty-output exit-0 no-op as genuine evidence,
  and a bad cmd: entry cannot be retracted'
state: in-progress
kind: bug
origin: human
created: '2026-09-06'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_evidence.py
- src/frob/app/ticket_runner/_verify.py
- src/frob/_cli_parsers/_ticket/_closeout.py
- docs/modules/tickets.md
- docs/modules/tickets-lifecycle.md
- docs/modules/tickets-landing.md
- src/frob/tickets/__init__.py
- src/frob/app/config.py
- src/frob/app/ticket_runner/_close_cmd.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/app/ticket_runner/_verify.py
  reason: 'part 3 (evidence removal/correction for cmd: entries) requires CLI wiring
    beyond _evidence.py; verified --replace''s new_node must resolve as a collected
    pytest/rust/other-language id (src/frob/app/ticket_runner/_verify.py:_apply_replace_evidence),
    so there is genuinely no path to correct a bad cmd: entry today'
  actor: logan
  at: '2026-09-06'
- op: add
  glob: src/frob/_cli_parsers/_ticket/_closeout.py
  reason: 'part 3 (evidence removal/correction for cmd: entries) requires CLI wiring
    beyond _evidence.py; verified --replace''s new_node must resolve as a collected
    pytest/rust/other-language id (src/frob/app/ticket_runner/_verify.py:_apply_replace_evidence),
    so there is genuinely no path to correct a bad cmd: entry today'
  actor: logan
  at: '2026-09-06'
- op: add
  glob: docs/modules/tickets.md
  reason: doc-coverage targets for symbols touched in _evidence.py/_verify.py
  actor: logan
  at: '2026-09-06'
- op: add
  glob: docs/modules/tickets-lifecycle.md
  reason: doc-coverage targets for symbols touched in _evidence.py/_verify.py
  actor: logan
  at: '2026-09-06'
- op: add
  glob: docs/modules/tickets-landing.md
  reason: doc-coverage targets for symbols touched in _evidence.py/_verify.py
  actor: logan
  at: '2026-09-06'
- op: add
  glob: src/frob/tickets/__init__.py
  reason: remove_evidence must be re-exported from frob.tickets.__init__ alongside
    replace_evidence/add_cmd_evidence, the existing pattern for every public evidence-family
    function
  actor: logan
  at: '2026-09-06'
- op: add
  glob: src/frob/app/config.py
  reason: AppConfig needs a ticket_evidence_remove field to carry --remove EVIDENCE-ID
    through, mirroring ticket_evidence_replace
  actor: logan
  at: '2026-09-06'
- op: add
  glob: src/frob/app/ticket_runner/_close_cmd.py
  reason: frob ticket close --evidence-cmd also calls _apply_cmd_evidence; --cwd DIR
    (T-4000) must be threaded through this call site too for consistent behavior with
    frob ticket evidence
  actor: logan
  at: '2026-09-06'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Consumer logand.app-v2 F-215, 2026-09-06. THIS IS A SILENT ZERO THAT WRITES
FALSE EVIDENCE INTO THE LEDGER, and it is the most severe consumer finding of
this drive.

WHAT HAPPENED. `--evidence-cmd` spawns argv directly with no shell, so
`cd frontend && npx vitest run ...` fails LOUDLY with SpawnFailed ('cd' is not an
executable) -- good, honest, easy to fix. The natural workaround is
`npx --prefix frontend <tool>`. For a non-npm binary that command DOES NOT FAIL:
npx tries to resolve the tool as an npm package, prints an interactive
"Did you mean help? [y/n]" prompt, receives no input because the run is
non-interactive, and STILL EXITS 0 WITH EMPTY STDOUT. frob records:

    cmd:... exit=0 sha256=e3b0c44298fc...

a genuine-looking evidence entry. e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
IS THE SHA256 OF THE EMPTY STRING. The command did nothing, proved nothing, and
was recorded as passing evidence. In the consumer's words, only "recognizing the
empty-string hash by eye" caught it -- and a less careful run "would have closed
a ticket on a no-op".

THIS IS THE DOMINANT DEFECT CLASS OF THIS CODEBASE, arriving at the one place it
does the most damage: the evidence ledger. Everything frob asserts about a ticket
being done rests on evidence being a real measurement. An exit-0 empty-output
command satisfies every check we currently apply.

THE FIX IS CHEAP AND SHOULD NOT WAIT FOR THE REST. The empty-string digest is a
known 64-hex constant. Refusing (or at minimum loudly warning on) a `cmd:`
evidence entry whose captured output is empty is a small, self-contained change
with an obvious fixture. DO NOT gate this behind the broader design questions
below.

BUT DO NOT STOP AT THE CONSTANT. Matching only e3b0c442... catches empty stdout
and misses the general case: a command that emits a banner and does no work, or
writes to stderr only. The empty digest is the cheap first cut; the honest
question is what makes a `cmd:` result EVIDENCE rather than an exit code, and it
should be stated on this ticket even if only the cheap cut ships now.

THE SECOND HALF IS A NO-EXIT, and it is why this cannot be closed with a warning
alone. The consumer reports there is NO WAY TO CORRECT A BAD cmd: ENTRY:
`--replace` only accepts a new id that resolves as a collected pytest/rust node
id, and there is no evidence-removal command. So a false `cmd:` entry, once
recorded, MUST REMAIN IN THE LEDGER alongside the corrected one. A system that
can record unfalsifiable evidence and cannot retract it is strictly worse than
one that never recorded it. VERIFY THIS CLAIM AGAINST THE CLI before designing --
it is a claim about our code -- but if true, an evidence-removal path is part of
this ticket, not a follow-up.

THE THIRD ASK IS THE ROOT CAUSE OF THE WORKAROUND: provide a documented `--cwd
DIR` for evidence-cmd. The user did not want `npx --prefix`; they wanted "run
this in that subdirectory". Direct-argv spawning is correct (it is why the `cd`
form failed honestly rather than silently), but with no --cwd the user is
FORCED into shell-ish workarounds, and one of those workarounds is what produced
the false evidence. Fixing --cwd removes the pressure that created the bug.

ALSO NOTED, worth verifying separately: the CLI's own error text says
`--evidence-cmd` is docs-kind only, yet this ux-kind ticket's calls succeeded.
Either the restriction is not enforced or the message is wrong; both are
defects, and a rule whose error text does not match its behaviour is its own
hazard.

MUST-FIRE FIXTURE: an evidence-cmd producing empty output is refused (or loudly
flagged), naming the empty digest.
MUST-STAY-QUIET: a real command with real output records normally.
THIRD FIXTURE: a recorded cmd: evidence entry can be removed or corrected.
FOURTH FIXTURE: --cwd runs the command in the named directory without a shell.

ACCEPTANCE
- Empty-output digest refused/flagged -- shippable on its own.
- The "what makes a cmd: result evidence" question stated, even if unresolved.
- Evidence removal/correction path, after verifying the no-exit claim.
- --cwd for evidence-cmd.
- The docs-kind-only restriction reconciled with observed behaviour.