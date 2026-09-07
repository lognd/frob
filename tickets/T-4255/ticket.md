---
id: T-4255
title: 'fix the Windows CLI and encoding test failures: TTY presumption, UTF-16 child
  output, and shell metacharacters'
state: in-progress
kind: bug
origin: human
created: '2026-09-07'
priority: high
parent: T-4236
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/system/test_cli_ticket.py
- tests/test_worktree_guard.py
- tests/test_tickets_evidence_cli.py
- src/frob/process/_tty.py
- src/frob/app/ticket_runner/_lifecycle.py
- src/frob/process/__init__.py
- src/frob/app/ticket_runner/_new.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/process/_tty.py
  reason: 'T-4255: shared cross-platform interactive-stdin check for the attach TTY
    fast-fail (sys.stdin.isatty() misreports True for NUL on Windows)'
  actor: logan
  at: '2026-09-07'
- op: add
  glob: src/frob/app/ticket_runner/_lifecycle.py
  reason: 'T-4255: wire the new cross-platform TTY check into the attach fast-fail
    path'
  actor: logan
  at: '2026-09-07'
- op: add
  glob: src/frob/process/__init__.py
  reason: 'T-4255: export the new is_interactive_stdin helper from frob.process'
  actor: logan
  at: '2026-09-07'
- op: add
  glob: src/frob/app/ticket_runner/_new.py
  reason: 'T-4255: reuse the same is_interactive_stdin mechanism for the clipboard-offer
    TTY gate, one mechanism instead of two ad hoc isatty() checks'
  actor: logan
  at: '2026-09-07'
designated_repro_test: null
acceptance:
- text: given the Windows runner, when the ticket CLI system test runs, then it passes
    and its interactivity premise matches what the child process actually observes
    there
  evidence: []
- text: given PowerShell-encoded child output, when the worktree guard test captures
    it, then the captured text decodes correctly and any product-side capture path
    is fixed too
  evidence: []
- text: given a command containing Windows shell metacharacters, when the evidence
    CLI builds it, then it passes an argument vector rather than a shell string
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
THE WINDOWS CLI AND ENCODING FAILURE GROUP. Three tests fail on the Windows CI
leg for reasons that are all about how a child process talks to us, not about
what the code under test decided. They are disjoint from the path-shape group
and from the land and lease group, so this ticket can be worked in parallel with
both.

WINDOWS IS VERIFIABLE LOCALLY. Do not reason about Windows behaviour from a
Linux shell, and never write that a fix is unproven until CI. The global winrun
script syncs this repository to a Windows mirror and runs a command there
natively through PowerShell. Measure the actual failing assertion on real
Windows BEFORE you change anything, and measure it again AFTER. A fix that was
never observed to change a Windows-side value is not evidence. Note that the
Windows virtualenv puts its executables in a Scripts directory, not a bin one.

THE THREE FAILURES.

First, a ticket CLI system test asserts on terminal-interactive behaviour. The
assertion presumes the child process sees a terminal, and the Windows runner
gives it something else. Determine what the child actually observes on Windows
before deciding whether the test premise or the product detection is wrong. If
the product decides interactivity by a mechanism that is simply absent on
Windows, that is a product defect and the fix belongs in the product.

Second, the worktree guard test compares captured child output against expected
text and the comparison fails because the captured bytes are UTF-16 encoded.
Every other byte is a null. That is the PowerShell default output encoding
reaching us undecoded. The question to answer by measurement is where the
decoding boundary should sit: the test harness that spawns the child, or the
product helper that captures child output. If any product code path captures
child output the same way, the fix must go there, because the test is only the
first observer of a defect every consumer would hit.

Third, an evidence CLI test builds a command containing characters that the
Windows shell treats as metacharacters. Find whether the product is building a
shell command string where it should be passing an argument vector. Quoting the
string is the wrong repair if the vector form is available.

WHAT ONE FIX LOOKS LIKE. Prefer one mechanism over three local corrections
wherever two of these share a cause. If they genuinely have three causes, say so
explicitly in the done report and fix all three.
