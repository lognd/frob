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

## Done report

Implemented item 3 of T-1719's plan only: `frob doctor` (src/frob/doctor.py)
now measures the on-PATH global `frob --version` against this
invocation's own version and reports the comparison as
`DoctorReport.global_binary` (a new `GlobalBinarySkew` model:
global_version/local_version/skewed). A measured disagreement makes
`healthy=False` and folds a remediation line naming both versions and the
reconcile command into `DoctorReport.remediation`, mirroring the
`.claude/hooks/frob-suggest.py` `frob-version-skew` nudge's own
spawn-strip-compare measurement (that hook already existed and covers the
interactive-command case; this is the same check surfaced through
`frob doctor` for a non-interactive/scripted caller). An unmeasurable
comparison (no global `frob` on PATH) never counts as skew.

Items 1 and 2 of T-1719's plan (fold `sync-claude-config.py` into a real
frob verb; gate the resulting drift in `frob check`) were NOT implemented
and are disclosed as cut, not silently dropped:

- Implementing the sync verb needs a new top-level subcommand wired
  through src/frob/app/app.py's `_RUNNER_MODULE_NAMES`/
  `_SUBCOMMAND_RUNNER_NAMES`/`_import_runner_module`, src/frob/app/
  config.py's `Subcommand` enum, and a new runner module -- all outside
  this ticket's narrowed scope (doctor.py/cli.md/test_doctor.py only,
  narrowed deliberately to avoid a broad lease blocking the fleet).
- Gating the drift needs `_KNOWN_GATE_RULES`/docs/modules/gates.md, both
  explicitly off-limits during this dispatch (held by other concurrent
  agents on T-1773/T-1735/T-1781), and logically depends on the sync verb
  existing first.

Filed as follow-ups (drafts, real ids assigned at land):
- T-1808: fold sync-claude-config.py into a frob verb.
- T-1809: gate the resulting drift once the verb exists.

Changed:
- src/frob/doctor.py::GlobalBinarySkew (new)
- src/frob/doctor.py::global_binary_skew (new)
- src/frob/doctor.py::_probe_global_frob_version (new, private)
- src/frob/doctor.py::_global_binary_skew_remediation (new, private)
- src/frob/doctor.py::DoctorReport (new global_binary field)
- src/frob/doctor.py::_combined_remediation/_collect_doctor_scans callers,
  _log_doctor_diagnosis, _assemble_doctor_report, run_diagnosis (threaded
  the new check through)
- docs/modules/cli.md (new section: frob doctor: global-vs-local frob
  binary skew (T-1719))

Evidence:
- tests/test_doctor.py::test_global_binary_skew_reports_disagreement
- tests/test_doctor.py::test_global_binary_skew_none_when_no_global_frob
- tests/test_doctor.py::test_global_binary_skew_not_skewed_when_versions_agree
- tests/test_doctor.py::test_run_diagnosis_unhealthy_on_global_binary_skew
- 13/13 tests/test_doctor.py pass (uv run pytest tests/test_doctor.py -q)

Gates: `uv run frob check --ticket T-1719` exit 0, all gate:* families
pass (ruff-check/ruff-format failures present are pre-existing repo-wide
debt in files this ticket never touched -- doctor.py/test_doctor.py/
cli.md are clean under both). `uv run frob check --land-parity` reports
clean (0 unscoped errors).

### Changed
```
 docs/modules/cli.md                |  33 +++++++++
 frob.lock                          |  20 +++++-
 src/frob/doctor.py                 | 139 ++++++++++++++++++++++++++++++++++---
 tests/test_doctor.py               |  81 +++++++++++++++++++++
 tickets/T-1719/ticket.md           |  37 +++++++++-
 tickets/T-1808/ticket.md |  49 +++++++++++++
 tickets/T-1809/ticket.md |  35 ++++++++++
 7 files changed, 381 insertions(+), 13 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 0 error(s), 612 warning(s), 734 waived
- error-findings: none (measured, zero errors)
