---
id: T-draft-07e7d209
title: 'frob.toml [commands] table plus a run verb: one declared home for every project
  command, sequences included'
state: queued
kind: feature
origin: human
created: '2026-09-19'
priority: high
parent: T-4757
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/policy/_models.py
- src/frob/app/run_runner.py
- src/frob/_cli_parsers/_core.py
- docs/commands/run.md
- tests/unit/test_run_commands.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: Given a [commands] entry that is an array of three steps, when it is run and
    the middle step exits non-zero, then execution stops there and the error names
    the failing step by index and command
  evidence: []
- text: Given an entry that references itself directly or transitively, when config
    is loaded, then it is refused with the full reference path printed
  evidence: []
- text: Given a project that declares no [commands] table, when test/lint/format/check
    are run, then they resolve to frob native verbs with no declaration
  evidence: []
- text: Given the dry-run form, when it is invoked, then the resolved sequence is
    printed and no subprocess is spawned
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Today a scaffolded project's workflow lives in a hand-written Makefile per
type (audit 5.1: six of seven types ship a full make surface). The owner's
decision is that wrappers are DERIVED from one declaration, never authored.

Add a [commands] table to frob.toml: a name mapped to what to run. frob's
own native verbs are the defaults, so a Python project declares nothing and
a cpp or cargo project declares its build and test entries once.

An entry's value is EITHER a single command OR an array run in order. Each
element is a shell-free argv, or the name of another entry, so a check entry
composing the fmt, lint and test entries is expressible. Semantics to
implement:

- execution stops at the first non-zero exit and the error names which step
  failed, by index and by command;
- every step is logged with its index, its command and its duration;
- a planned dry-run flag on the new run verb prints the resolved sequence
  without executing it;
- reference cycles between entries are refused at config-load time, with the
  full reference path printed;
- generated wrapper targets only ever invoke the run verb by entry name;
  they never expand a sequence inline, so a sequence has exactly one home.

Also add the run verb (execute one entry by name) and make a build verb
delegate to the build entry rather than carrying its own logic.

The rendered frob.toml must be readable on a first pass: section order
project, profile, commands, testing, gates (refs only where an exception
exists); each table header preceded by one plain-English comment saying what
it controls and when you would edit it; no ticket ids or change history in
comments; defaults omitted rather than spelled out; commands entries read
like a task list.

Scope note: the closed top-level frob.toml schema and the
conventional-files-referenced-by-default change are NOT in this leaf -- they
are already filed as T-draft-538a0625, which this story blocks the scaffold
frob.toml leaf on.

Positive controls (each an assert, not a smoke test):
1. a three-step entry runs its steps in declared order and, when the MIDDLE
   step exits non-zero, the run stops there and the error carries that
   step's index;
2. an entry that references itself (directly or through a second entry) is
   refused at load with the reference path in the message;
3. a project declaring no commands table still resolves test, lint, format
   and check to frob's native verbs;
4. the dry-run form prints the fully resolved sequence and executes nothing
   (asserted by a subprocess spy, not by exit code).
