---
id: T-3978
title: A scope glob matching zero tracked files is accepted silently, granting a lease
  over nothing (5 instances in one session)
state: queued
kind: ux
origin: human
created: '2026-09-06'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_scope.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
A SCOPE GLOB THAT MATCHES ZERO TRACKED FILES IS ACCEPTED SILENTLY. Because scope
is a WRITE LEASE, that grants a lease over nothing: the ticket looks scoped, the
implementer starts, and either has to widen immediately (losing the guarantee the
scope was supposed to give) or edits outside scope.

MEASURED, FIVE TIMES IN ONE SESSION, BY TWO DIFFERENT ACTORS, 2026-09-06:
  - T-3944 filed with src/frob/app/ticket_runner/_scope_cmd.py -- no such file.
  - T-3943 filed with _query.py, which carries neither the hardcoded diff base
    nor the base_ref plumbing the ticket is about.
  - T-3946 filed with _cli_parsers/_ticket/_evidence.py -- no such file (the
    three --accepts definitions are all in _closeout.py).
  - A planner agent did the same twice, on T-3954 and T-3955.
All five had the same cause: a plausible module name generated from the VERB name,
which feels exactly like recall. This is not carelessness that more care fixes --
it is a guess that is indistinguishable from a memory at the moment it is made,
which is precisely when a machine check earns its keep.

THE SILENT-ACCEPT ALSO POISONS THE ONE SIGNAL THAT WOULD CATCH IT. Scope overlap
warnings are computed against the glob, so a glob matching nothing reports ZERO
OVERLAPS -- which reads as "cleanly disjoint" and is actually "matches nothing".
T-3943 printed three overlap warnings; T-3944 printed none, and the silence was
the tell I walked past.

WHY THIS IS NOT ALREADY COVERED, and the constraint any fix must respect.
`_is_new_concrete_file_glob` in src/frob/tickets/_scope.py:466 DOES test
existence, but deliberately only as a narrow carve-out signal, and its docstring
states the reason a bare does-not-exist check is unsafe: "test fixtures routinely
run against an empty tmp_path, where EVERY path does not exist yet, so existence
alone is not a safe signal outside a real checkout." That objection is correct
and must not be broken.

THE DISTINGUISHING SIGNAL THE DOCSTRING POINTS AT: compare against GIT-TRACKED
files, not the filesystem. A glob matching zero tracked files IN A REPO THAT HAS
TRACKED FILES is a real checkout with a bad glob; an empty tmp_path fixture has
no tracked files at all and is therefore naturally excluded. Verify that
distinction actually holds for the fixture shapes this repo uses before relying
on it -- that is the crux of the ticket.

WARN, DO NOT REFUSE. There are legitimate not-yet-existing scopes (a ticket whose
whole job is to create a file), which is exactly what the T-0561 carve-out exists
for. A refusal would break those. A warning naming the glob and saying it matches
no tracked files is enough -- the failure mode here is silence, not permission.

DO NOT fix this by documenting "check your scope paths". I wrote that rule for
myself mid-session and then broke it again minutes later; the planner broke it
twice while under an explicit instruction not to. Written guidance has now failed
five times against this specific error.

MUST-FIRE FIXTURE: a scope glob matching zero tracked files in a populated repo
warns, naming the glob.
MUST-STAY-QUIET: (a) a glob matching tracked files does not warn; (b) a ticket
legitimately scoping a not-yet-created test file still works, per the T-0561
carve-out -- this is the regression that would otherwise be introduced.
THIRD FIXTURE: an empty-tmp_path fixture repo does not warn, proving the
git-tracked signal separates the two cases.

ACCEPTANCE
- Warning fires on a zero-match glob in a real checkout, naming the glob.
- The T-0561 new-test-file carve-out is demonstrably unbroken.
- Test fixtures against empty repos do not become noisy.
- All fixtures committed.