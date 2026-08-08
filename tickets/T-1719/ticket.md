---
id: T-1719
title: Fold Claude-config sync into a frob verb, gate the drift, and report global-vs-local
  frob skew in doctor
state: done
kind: feature
origin: agent
created: '2026-08-07'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/doctor.py
- docs/modules/cli.md
- tests/system/test_cli_doctor.py
- tests/test_doctor.py
- tickets/T-1719/**
- frob.lock
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/app/ticket_runner/__init__.py
  reason: narrow to doctor.py global-vs-local-skew reporting only; folding sync into
    a frob verb + gating drift needs app.py/config.py/new runner + gates registry,
    all outside a narrow lease and partly held by other agents
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tests/system/test_cli_doctor.py
  reason: scope closure requires doctor.py's existing frob:tests target file
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tests/test_doctor.py
  reason: add unit test home for the new global-vs-local skew check
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tickets/T-1719/**
  reason: SCOPE001 flags the ticket's own ticket.md/done-report.md under v2 storage;
    declare it explicitly rather than relying on an undocumented implicit exemption
  actor: logan
  at: '2026-08-08'
- op: add
  glob: frob.lock
  reason: frob ack on doctor.py::run_diagnosis (its digest moved from this ticket's
    own edit) writes the ack into frob.lock
  actor: logan
  at: '2026-08-08'
evidence:
- tests/test_doctor.py::test_global_binary_skew_reports_disagreement
- tests/test_doctor.py::test_global_binary_skew_none_when_no_global_frob
- tests/test_doctor.py::test_global_binary_skew_not_skewed_when_versions_agree
- tests/test_doctor.py::test_run_diagnosis_unhealthy_on_global_binary_skew
designated_repro_test: null
threat: null
component: null
---
Shared Claude config (PreToolUse hooks, the agent playbook) is now
git-tracked in `.claude/hooks/` and materialised into `~/.claude/` by
`.claude/hooks/sync-claude-config.py`, with `--check` reporting drift and a
SessionStart hook surfacing it. That closes the immediate hole -- a hook
that existed only in one home directory was an undocumented repo-wide
behaviour change no review ever saw.

But the sync script is a loose Python file in `.claude/`, which is exactly
the shape this repo's standing directive rejects: workflows belong in frob
subcommands, not in ad-hoc scripts. It is also unenforced -- `--check` runs
only if someone wires it up, and nothing fails a gate when the copies
drift.

Two pieces of work.

1. FOLD THE SYNC INTO frob. A verb (`frob claude sync` / `frob agent sync`,
   name it as fits the CLI regrouping in T-1567..T-1571) that:
   - reads its managed-file manifest from `frob.toml` rather than a
     hard-coded list in a script, so a repo declares what it publishes;
   - writes each destination behind the do-not-edit banner, atomically
     (write-temp-then-replace -- a half-written hook fails to parse on
     every subsequent tool call);
   - never syncs global -> repo, and never touches a path outside the
     manifest (`~/.claude/` holds plenty this repo has no business
     owning);
   - `--check` exits non-zero on drift, with the drifted paths NAMED. An
     error that does not name its own cause has cost this repo three
     separate fleet stalls already.

2. GATE IT. A rule (CLAUDE001, or the next free id -- register it in the
   rule catalog, do not invent an unregistered one) that fails when a
   managed file differs from its materialised copy. Drift is currently
   invisible to `frob check`, which means the tracked original can say one
   thing while every agent reads another. That is the same
   catalogued-but-not-enforced shape this repo has been burned by before:
   a registry nobody reads is documentation, not enforcement.

Also in scope, because it is the same reconciliation problem:

3. GLOBAL frob IS NOT LOCAL frob, AND NOTHING SAYS SO. Measured today:
   `frob` on PATH is 0.184.0 while this repo's `uv run frob` is 0.361.0 --
   177 versions apart. Every gate number the global build reports for this
   tree is wrong, and nothing surfaces that. `frob doctor` should report
   the skew explicitly (both versions, and the reconcile command), and the
   hook's cached measurement should be the same code path rather than a
   second implementation that can disagree with it.

The `frob-suggest.py` rule table should move with the sync verb, but the
BLOCK-ONCE-THEN-ALLOW semantics must be preserved exactly: the first
attempt at a matching command is denied with a suggestion, an identical
re-run is allowed. A suggestion that cannot be overridden is a policy, and
this deliberately is not one -- it blocked its own authoring commit on a
prose parenthetical within an hour of being written, and the override was
the only thing that made that recoverable.