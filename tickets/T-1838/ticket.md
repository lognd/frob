---
id: T-1838
title: frob:waive comments in .claude/hooks/** never take effect (BUILTIN_SKIP_DIRS
  prunes .claude from frob.graph's walk)
state: queued
kind: bug
origin: human
created: '2026-08-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/excludes.py
- src/frob/graph/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
`frob.excludes.BUILTIN_SKIP_DIRS` includes `".claude"`, so `frob.graph`'s
source walk (the one `frob.gates._waive._waivers_by_rule` and the
SELFAUDIT/SYS100 capability-declaration machinery both read WAIVE/design
edges from) never parses ANY file under `.claude/hooks/**` -- confirmed
directly: `src/frob/app/telemetry.py`'s `# frob:waive SEC110 reason=...`
shows up as `[waived: ...]` in `frob check` output, but the byte-identical
comment placed on `.claude/hooks/dispatch-telemetry.py` (T-1787) does not,
and grepping a full `frob check` run for `.claude/hooks.*waived:` returns
zero matches repo-wide -- no `.claude/hooks/**` waiver has ever taken
effect, for any file, any rule.

Meanwhile `gate:SEC` (SEC110) and `gate:ARCH` (ARCH103) DO scan
`.claude/hooks/**` directly (they found real, correct findings in
dispatch-telemetry.py) via a walk that does NOT respect
`BUILTIN_SKIP_DIRS`'s `.claude` entry -- so a hook script that reads any
env var (the standard `FROB_NO_TELEMETRY` opt-out check every other
telemetry call site in this repo carries) or has a 2-branch function trips
an UNWAIVABLE gate error, structurally, no matter how the reason is
written or where the comment is placed.

Found while working T-1787 (dispatch telemetry hooks): SEC110 on
`.claude/hooks/dispatch-telemetry.py:71`'s `os.environ.get("FROB_NO_TELEMETRY", ...)`
and ARCH103 on the same file's `_current_branch` helper are both real,
correctly-detected findings that cannot be waived through any means
available inside a ticket's own scope -- fixing it requires either (a)
removing `.claude` from `BUILTIN_SKIP_DIRS` for `frob.graph`'s walk (so
`.claude/hooks/**` waivers/design edges resolve, matching what the
scanning gates already see), or (b) making SEC/ARCH's own scan respect the
same exclude set `frob.graph` uses, so a directory invisible to waivers is
also invisible to the gates that would need one.

Landed with these two findings present and undisclosed-waivable; see
T-1787's Done report.

CORRECTION (T-1839's post-land sweep fix, commit c14906e75): the SEC110
finding on `.claude/hooks/dispatch-telemetry.py` WAS actually waivable --
moving the `# frob:waive SEC110 reason=...` comment onto its own line
directly ABOVE a single-line `os.environ.get(...)` call (rather than
trailing on the call's own closing-paren line, which is what the T-1787
version had) made the waiver take effect. This narrows this ticket's
diagnosis: it is NOT true that no `.claude/hooks/**` waiver can ever take
effect (SEC110 clearly can, once correctly placed) -- what remains
unconfirmed is whether the SAME comment-placement fix would have worked
for the ARCH103 finding this ticket also cited (moot for T-1787's own
case, since that finding was independently eliminated by a refactor, not
waived) or for OTHER gate families' waivers under `.claude/hooks/**`.
Retest before doing the BUILTIN_SKIP_DIRS fix this ticket proposes --
the root cause may be narrower (a waive-comment-placement parsing
quirk specific to single- vs multi-line statements) rather than the
whole-directory graph-pruning theory this ticket's body argues for.
