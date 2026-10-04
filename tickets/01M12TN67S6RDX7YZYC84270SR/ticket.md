+++
id = "01M12TN67S6RDX7YZYC84270SR"
title = "'no grammar registered for extension .md' internal call-site hint leaks into ticket verb output"
type = "bug"
category = "done"
outcome = "wont-fix"
priority = "low"
reporter = "human"
created = "2026-08-28T00:00:00Z"
updated = "2026-10-04T21:08:47Z"
aliases = ["T-3321"]
labels = ["milestone:1.1.0", "v1-cluster:D2"]
scope = ["src/frob/app/ticket_runner/_verify.py"]
+++

REPORTED FROM REAL CONSUMER USE (../diax FROBLEMS.md F-015).

Every `frob ticket scope/start/evidence/close/land` prints:
    WARNING: no grammar registered for extension '.md' (path=docs/index.md,
    site=parse_file); pass expect_heterogeneous=True at the call site if
    this is routine

This is an internal call-site implementation hint ("pass
expect_heterogeneous=True at the call site") leaking into normal user-facing
output on every single ticket verb invocation -- pure noise for a routine,
expected condition (a .md file with no registered grammar is apparently
normal here, given how often this fires). Either the call site should pass
that flag (silencing it correctly, if the condition really is routine), or
the log level should drop to DEBUG so it stops appearing in default output.

WHAT TO BUILD: find the `parse_file` call site processing docs/index.md (or
whichever doc triggers it in a typical repo) during ticket verbs, and either
pass `expect_heterogeneous=True` there if that is the CORRECT fix per the
warning's own suggestion, or demote the log level if the call site
genuinely cannot know in advance. State which in the Done report.

MUST-FIRE / MUST-STAY-QUIET: `frob ticket scope`/`start`/`evidence`/`close`/
`land` in a repo with a `.md` doc with no registered grammar -- 0 WARNING-
level output for this specific condition (either silenced correctly or
demoted); a genuinely NEW/unexpected grammar-resolution failure elsewhere
must still surface at an appropriate level.
