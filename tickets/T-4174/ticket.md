---
id: T-4174
title: a scope entry containing a space is accepted and matches nothing, so every
  scope-derived judgement about that ticket is vacuous
state: queued
kind: bug
origin: agent
created: '2026-09-07'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_models.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given a scope entry containing a space, when it is declared, then it is either
    split into its parts or refused with a message naming it
  evidence: []
- text: given a declared scope entry that matches zero tracked files, when it is declared,
    then that is reported to the author
  evidence: []
- text: given the existing ticket queue, when audited, then the count of scope entries
    matching zero tracked files is reported
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
A SCOPE ENTRY CONTAINING A SPACE IS ACCEPTED AND MATCHES NOTHING. Found while
investigating a stale lease, not reported by anyone -- which is the point: a
ticket has been carrying a scope that covers zero files for two days and no check
noticed.

MEASURED, T-3811's declared scope as stored:

    scope:
    - pyproject.toml uv.lock

ONE entry, two paths, joined by a space. Tested against frob's own matcher:

    scope_matches('pyproject.toml', ['pyproject.toml uv.lock'])   -> False
    scope_matches('uv.lock',        ['pyproject.toml uv.lock'])   -> False
    scope_matches('pyproject.toml', ['pyproject.toml','uv.lock']) -> True
    scope_matches('uv.lock',        ['pyproject.toml','uv.lock']) -> True

So the ticket's scope matches neither of the two files it names. Every
scope-derived judgement about that ticket is therefore vacuous: its lease claims a
path that cannot collide with anything, and any coverage or containment question
asked of it has a meaningless answer. This is the silent-zero shape applied to a
DECLARATION rather than to a measurement -- the field is present, looks
reasonable, and does nothing.

THE CAUSE IS A HALF-DEFENSIVE SPLIT. `_split_scope_entries` exists precisely to
re-split entries defensively -- its docstring says it handles comma-joined values
even though the models normalise on construction. It splits on COMMAS. It does not
split on whitespace. So a caller who passes two paths inside one quoted shell
argument gets a single dead glob, while a caller who uses a comma is repaired
silently. One separator is defended, the other is not, and the two produce
opposite outcomes from equally plausible input.

WHY THIS MATTERS BEYOND ONE TICKET. Scope is not decoration -- it is the lease, the
coverage denominator, and the containment check. A scope that matches nothing does
not fail loudly; it makes every question about the ticket unanswerable in the
direction that looks like success. And nothing in the system flags it: the ticket
has sat queued with this scope since 2026-09-05.

THE GENERAL FORM IS THE REAL FIX. A declared scope entry that matches ZERO tracked
files is almost always a typo, a shell-quoting accident, or a path that has since
moved. This repo already built the primitive for exactly this class -- the
subject-count work established that a rule examining zero subjects is a finding
rather than a pass, and a related ticket applies it to declaration globs that
match no file. A scope entry matching nothing belongs in that same family. Check
whether that machinery can be reused rather than adding a fourth bespoke check.

WHAT TO DO
  1. Decide, and state, whether whitespace is a separator in a scope entry. Either
     split on it as commas are split, or REFUSE the entry with a message naming
     the offending value. Silently accepting it is the current behaviour and is
     the defect. Refusing is probably better than splitting: a path may legally
     contain a space, and guessing wrong on a real filename would be worse.
  2. Warn when a declared scope entry matches zero tracked files, at declaration
     time, where the author can still fix it cheaply.
  3. Audit the existing queue for other zero-matching scope entries and report the
     count. This one was found by accident while chasing something else; there is
     no reason to think it is unique.
  4. Note that T-3811 itself duplicates already-landed work on the same
     dependency; it should be dropped separately once this ticket has taken what
     it needs from it as a reproduction.

MUST-FIRE FIXTURE:   a scope entry containing a space is either split into its
                     parts or refused with a message naming it -- not stored
                     as a glob that matches nothing.
MUST-STAY-QUIET:     a legitimate single path that genuinely contains a space is
                     handled per the decision above, and the decision is stated
                     on the function.
THIRD FIXTURE:       a declared scope entry matching zero tracked files is
                     reported at declaration time.

ACCEPTANCE
- The whitespace question decided explicitly and enforced.
- Zero-matching scope entries reported when declared.
- The existing queue audited, with the count of other dead scope entries reported.
- Reuse of the existing zero-subject machinery evaluated rather than a new check
  invented.
- All three fixtures committed.
