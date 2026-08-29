---
id: T-3326
title: frob check --fix is repo-wide even from a targeted invocation, and a killed
  run leaves an unrecorded partial rewrite
state: in-progress
kind: bug
origin: human
created: '2026-08-28'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_fix_engine.py
- src/frob/app/check_runner.py
- src/frob/_cli_parsers/_check.py
- src/frob/app/config.py
- docs/commands/check.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/app/check_runner.py
  reason: T-3326's own acceptance criteria requires --fix to honour --ticket scope
    and gate the unscoped repo-wide case behind an opt-in -- both require the CLI
    wiring (check_runner.py's _apply_tier_a_and_reverify never threads ticket_id through
    to apply_tier_a_fixes despite cfg.check_ticket being available) plus a new --fix-all
    opt-in flag (cli parser + AppConfig)
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/_cli_parsers/_check.py
  reason: T-3326's own acceptance criteria requires --fix to honour --ticket scope
    and gate the unscoped repo-wide case behind an opt-in -- both require the CLI
    wiring (check_runner.py's _apply_tier_a_and_reverify never threads ticket_id through
    to apply_tier_a_fixes despite cfg.check_ticket being available) plus a new --fix-all
    opt-in flag (cli parser + AppConfig)
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/app/config.py
  reason: T-3326's own acceptance criteria requires --fix to honour --ticket scope
    and gate the unscoped repo-wide case behind an opt-in -- both require the CLI
    wiring (check_runner.py's _apply_tier_a_and_reverify never threads ticket_id through
    to apply_tier_a_fixes despite cfg.check_ticket being available) plus a new --fix-all
    opt-in flag (cli parser + AppConfig)
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/app/check_runner.py
  reason: T-3326's own acceptance criteria requires --fix to honour --ticket scope
    and gate the unscoped repo-wide case behind an opt-in -- both require the CLI
    wiring (check_runner.py's _apply_tier_a_and_reverify never threads ticket_id through
    to apply_tier_a_fixes despite cfg.check_ticket being available) plus a new --fix-all
    opt-in flag (cli parser + AppConfig)
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/_cli_parsers/_check.py
  reason: T-3326's own acceptance criteria requires --fix to honour --ticket scope
    and gate the unscoped repo-wide case behind an opt-in -- both require the CLI
    wiring (check_runner.py's _apply_tier_a_and_reverify never threads ticket_id through
    to apply_tier_a_fixes despite cfg.check_ticket being available) plus a new --fix-all
    opt-in flag (cli parser + AppConfig)
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/app/config.py
  reason: T-3326's own acceptance criteria requires --fix to honour --ticket scope
    and gate the unscoped repo-wide case behind an opt-in -- both require the CLI
    wiring (check_runner.py's _apply_tier_a_and_reverify never threads ticket_id through
    to apply_tier_a_fixes despite cfg.check_ticket being available) plus a new --fix-all
    opt-in flag (cli parser + AppConfig)
  actor: logan
  at: '2026-08-29'
- op: add
  glob: docs/commands/check.md
  reason: will document the new --fix-all opt-in flag and the --ticket-scoped --fix
    behavior here
  actor: logan
  at: '2026-08-29'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
OBSERVED 2026-08-28 by Series DW while landing T-3283, and reported by it as a
caution rather than swallowed -- which is the only reason we know.

An unscoped `frob check --only sys --fix`, run to re-baseline one ratchet lock
file, APPLIED TIER-A FIXES REPO-WIDE, touching roughly 15 unrelated files,
before being killed by host memory pressure partway through. The agent reverted
everything and kept only the intended lock bump. Nothing was lost. That is the
good outcome, and it was luck plus a careful agent, not a property of the tool.

THE HAZARD HAS TWO INDEPENDENT HALVES, and both need answering:

  1. BLAST RADIUS. There is no way to say "fix only what I am working on".
     `--fix` operates over everything the selected gates report, so a targeted
     one-file intent becomes a repo-wide rewrite. In a fleet where several
     agents hold scope leases on different files, one agent's `--fix` can
     rewrite files another agent is mid-edit on. `frob check --ticket <id>`
     already exists and knows a ticket's declared scope; `--fix` does not
     appear to respect it.

  2. PARTIAL APPLICATION. The run was KILLED PARTWAY. So `--fix` can leave a
     tree with an arbitrary prefix of its edits applied and no record of where
     it stopped. There is no journal, no "fixes applied so far" summary on
     death, and no resume. The recovery path was `git`, and only because the
     agent noticed. An agent that did not notice would have committed a dozen
     unrelated Tier-A rewrites under an unrelated ticket -- which is precisely
     the CrossTicketLeakage/passenger-carry class this repo already guards
     against at land time, arriving through a door the land guard never sees
     because the edits are already in the worktree by then.

WHY THIS IS RELEASE-RELEVANT: `frob check --fix` is a documented, user-facing
command, and the owner is preparing frob's first real PyPI release. A new user
running it to fix one finding gets a repo-wide rewrite of a codebase they have
not yet learned to trust. The scaffold's own docs steer users toward `make
check`; the moment they reach for `--fix` this is what they get.

WHAT TO BUILD -- decide, do not guess, and state your reasoning:
  a. `--fix` should respect `--ticket <id>`'s declared scope when both are
     given. That is the narrow, obviously-correct half.
  b. For the unscoped case, decide between: refusing without an explicit
     opt-in flag (e.g. `--fix-all`), or proceeding but PRINTING the file list
     and count BEFORE writing anything. Do not make it silently repo-wide.
  c. Make partial application recoverable: at minimum, report every file
     already modified when the process dies, so a killed run leaves a
     readable record instead of an unexplained dirty tree. A journal that
     supports resume is better but may be out of scope -- say which you chose.

DO NOT FIX THIS BY REMOVING OR CRIPPLING `--fix`. The Tier-A auto-fix engine
(T-1137 epic, T-1138/T-1260/T-1261) is real, useful, and this repo's land
pipeline depends on it. A repo-wide fix pass is a legitimate operation; it just
must not be the ACCIDENTAL default of a targeted invocation.

CHECK FOR THE SIBLING CASE AND REPORT IT: the land pipeline runs its own
pre-land Tier-A fix pass. Determine whether that pass is scoped to the landing
ticket or is equally repo-wide -- if it is repo-wide, that is a second, more
serious instance of the same hazard, because it runs unattended on every land.
Report the answer; do not fix it here unless it is the same code path.

MUST-FIRE FIXTURE: `frob check --ticket <id> --fix` modifies no file outside
that ticket's declared scope.
MUST-STAY-QUIET FIXTURE: a deliberate repo-wide fix pass still works when
explicitly requested.
THIRD FIXTURE: a `--fix` run interrupted partway reports which files it had
already modified.

ACCEPTANCE
- `--fix` honours `--ticket` scope.
- The unscoped case is either opt-in or announces its file list before writing.
- A killed run leaves a readable record of what it touched.
- A stated answer on whether the pre-land Tier-A pass has the same blast radius.
- All three fixtures present.
