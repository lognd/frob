---
id: T-3510
title: Force UTF-8 for the remaining charmap-vulnerable text I/O path(s)
state: queued
kind: bug
origin: human
created: '2026-08-30'
priority: medium
parent: T-3505
tier: ticket
sprint: null
runs_last: false
milestone: 1.0.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/design/windows-portability.md
scope_breadth_ack: true
scope_breadth_ack_reason: exact file(s) not yet identified from T-3076's log; placeholder
  scope, first step of the ticket body is pinning down the real file(s) then narrowing
  via scope --add/--remove
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Force UTF-8 for text I/O that currently relies on the platform default
encoding, so Windows' narrower default 'charmap' codec never raises on
characters the codec can't represent.

MEASURED: 2 of T-3076's 278 windows-only failures are
UnicodeEncodeError: 'charmap' codec can't encode character. Smallest
of the five primitive buckets, but a real correctness gap: any output
path that hits a non-ASCII (or certain Unicode) character on Windows
without an explicit encoding= will use the legacy 'mbcs'/'charmap'
codec instead of UTF-8, unlike POSIX where UTF-8 is normally the
default.

DESIGN: identify the SPECIFIC write path(s) T-3076's log shows raising
(likely print()/sys.stdout writes, or a Path.open()/read_text()/
write_text() call missing encoding="utf-8" -- most of this codebase's
existing read_text/write_text calls already pass encoding="utf-8"
explicitly per the survey grep below, so the 2 failures are most
likely an un-audited console/stdout write or a rare read_text/open
call that is missing the explicit kwarg). Fix at the source: add
encoding="utf-8" (or errors="replace"/"backslashreplace" only where
the doctrine explicitly allows lossy display, never for data at rest)
to the specific call site(s), and where the failure is a
console/stdout write rather than a file, reconfigure that stream
(`sys.stdout.reconfigure(encoding="utf-8")`) at the narrowest possible
scope rather than globally monkeypatching I/O.

FILES IN SCOPE: to be pinned down from T-3076's actual GHA log
(run 33035660969) at the two exact failing test node ids -- this
ticket's first step is identifying them precisely (the log excerpt in
T-3076 does not name the file), then scoping narrowly to that file (or
files) plus its test. Do NOT widen this ticket's scope to every
read_text/write_text call in the repo; the existing survey
(`git grep -n 'encoding=' -- src`) shows most I/O already pins UTF-8
explicitly, so this is a 1-2 file gap, not a repo-wide encoding audit.

MUST-FIRE
- The identified UnicodeEncodeError call site(s) use UTF-8 explicitly
  (file I/O) or a reconfigured UTF-8 stream (console output).
- The 2 windows-only charmap failures collapse.

MUST-STAY-QUIET
- No existing encoding="utf-8" call site changes behavior.
- POSIX output is byte-for-byte unchanged.

SCOPE GROUPING: scope-disjoint from the fcntl, os.sysconf, AF_UNIX and
fork-context leaves -- dispatchable in parallel with all four. Smallest
leaf; good candidate to dispatch first if agent capacity is scarce.
