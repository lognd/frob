---
id: T-3322
title: frob ticket new hung indefinitely in a WSL2 9p RPC after writing the ticket
  file
state: done
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
- src/frob/app/ticket_runner/_new.py
- tests/unit/test_app_runners_batch7.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_app_runners_batch7.py
  reason: existing clipboard-prompt tests must set the new FROB_TICKET_NEW_CLIPBOARD
    opt-in env var to keep exercising the interactive path after T-3322's second gate
  actor: logan
  at: '2026-08-30'
evidence:
- tests/unit/test_app_runners_batch7.py::TestClipboardAttachOnNew::test_no_clipboard_image_skips
- tests/unit/test_app_runners_batch7.py::TestClipboardAttachOnNew::test_declined_answer_skips_attach
- tests/unit/test_app_runners_batch7.py::TestClipboardAttachOnNew::test_accepted_answer_attaches
- tests/unit/test_app_runners_batch7.py::TestClipboardAttachOnNew::test_env_var_unset_never_calls_clipboard_has_image_even_on_a_tty
- tests/unit/test_app_runners_batch7.py::TestClipboardAttachOnNew::test_env_var_set_but_not_a_tty_never_calls_clipboard_has_image
designated_repro_test: tests/unit/test_app_runners_batch7.py::TestClipboardAttachOnNew::test_env_var_unset_never_calls_clipboard_has_image_even_on_a_tty
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 64b291eca4a1ea5ebeae0391d3e03700b42d7d55
---
REPORTED FROM REAL CONSUMER USE (../diax FROBLEMS.md F-023). WORK-DESTROYING
CLASS OF BUG (an indefinite hang, not a crash) -- this repo runs on WSL2
routinely (see this repo's own standing notes on WSL/9p issues), so this is
not an exotic environment for frob's actual users.

The 51st `frob ticket new` in a scripted batch wrote
tickets/T-draft-bfbd192f/ticket.md successfully and then NEVER EXITED.
`/proc/<pid>/wchan` showed `p9_client_rpc` -- the WSL2 Windows-drive (9p)
bridge. Nothing in the command names a Windows path. Reporter's suspicion:
either a clipboard-image probe ("TTY + clipboard image -> offers mockup
attach") or a telemetry/home-config hash reaching into /mnt/c. stdin was
`/dev/null` in this run, so an isatty(stdin)-gated probe should not have
fired at all -- if it did anyway, that gate itself is broken, not just
under-scoped.

WHAT TO BUILD:
  1. Locate `_maybe_attach_clipboard_image` (src/frob/app/ticket_runner/
     _new.py:847, seen directly in this repo's own source) and confirm
     whether it is properly gated on `isatty(stdin)`, and whether ANY code
     path in `frob ticket new` touches `/mnt/*` or otherwise crosses the 9p
     boundary unconditionally (a telemetry/config hash reading a Windows-
     side path, per the reporter's second hypothesis).
  2. Whichever is the real cause, fix it so `frob ticket new` NEVER touches
     `/mnt/*` implicitly, and gate the clipboard probe on isatty(stdin) AND
     an explicit flag (per the reporter's own suggestion) rather than
     isatty alone, since isatty alone apparently did not prevent this hang.
  3. If neither hypothesis reproduces after real investigation, say so
     plainly and describe what was ruled out -- do not guess-fix without a
     confirmed mechanism for something this severe.

MUST-FIRE / MUST-STAY-QUIET: 51+ sequential `frob ticket new` calls with
stdin=/dev/null on WSL2 -- every call must exit within a bounded time, none
may block on a 9p RPC.