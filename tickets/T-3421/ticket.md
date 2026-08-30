---
id: T-3421
title: root-write guard matches redirects lexically, refusing read-only commands and
  any text that merely mentions a redirect
state: queued
kind: bug
origin: human
created: '2026-08-29'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .claude/hooks/root-write-guard.py
- tests/test_hook_root_write_guard.py
- docs/guides/claude-hooks.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: .claude/hooks/root-write-guard.py
  reason: T-3421 fixes the root-write guard's redirect matching -- this is the only
    file that implements it
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/test_hook_root_write_guard.py
  reason: root-write-guard tests + its doc anchor page, needed for a redirect-parsing
    fix and its fixtures
  actor: logan
  at: '2026-08-29'
- op: add
  glob: docs/guides/claude-hooks.md
  reason: root-write-guard tests + its doc anchor page, needed for a redirect-parsing
    fix and its fixtures
  actor: logan
  at: '2026-08-29'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
The root-write guard scans the RAW TEXT of a command -- including inside single
quotes and inside heredoc bodies -- for redirect-looking character sequences. It
does not parse shell tokens, so it refuses commands that provably write nothing.

MINIMAL POSITIVE CONTROL, measured 2026-08-29. Writing the operator as GTE here
so this ticket body does not itself trip the bug:

    echo 'x GTE y'        -> REFUSED as a root write
    echo hello            -> allowed
    echo hi REDIR /tmp/... -> allowed

An `echo` of a single-quoted string cannot write anywhere. The sequence sits
inside quotes, where the shell treats it as literal text. The guard fired
anyway. The two controls beneath it show the guard is not simply refusing
everything, and not refusing all redirects -- a genuine redirect to /tmp is
correctly allowed. It is specifically the character sequence that triggers it.

HOW IT WAS FOUND, so the cost is on record as measured rather than theoretical.
Four consecutive commands were refused while extracting pytest assertion text
from a log file under /tmp:

  1. a sed-grep-head pipeline whose grep pattern contained a caret and the
     redirect character
  2. an awk program with a numeric range comparison inside single quotes
  3. a python heredoc whose body contained a numeric comparison
  4. a heredoc writing a ticket body to /tmp, whose BODY TEXT quoted example
     redirects while explaining this very bug

Case 4 is the sharpest: the guard read the CONTENT being written to a /tmp file
and refused the command because that content described a redirect. A document
about redirects cannot be written from this directory.

None of the four writes anything into the checkout. All four read or write only
under /tmp. The practical effect is that ordinary numeric comparison -- awk
ranges, python conditionals, shell arithmetic -- and any prose discussing shell
redirection are unusable from the shared root, which is exactly where a
coordinator does read-only measurement work.

WHY THIS IS THE STANDING "TOKEN, NOT LEXICAL" RULE AGAIN. The repo's own
directive is that checks must parse and compare SYMBOLS, never substrings. A
guard deciding "this is a redirect" by scanning characters cannot distinguish:

  - a real redirect whose target resolves inside the checkout   (must refuse)
  - the same characters inside single or double quotes          (must allow)
  - the same characters inside a heredoc body                   (must allow)
  - a file-descriptor redirect such as stderr onto stdout       (must allow)
  - a redirect whose target resolves under /tmp                 (must allow)

WHAT TO BUILD. Tokenize the command and decide on the PARSED redirect target,
not on raw text. Python's `shlex` resolves quoting correctly; the fix is to ask
the parser where the redirect points, then resolve that path and compare it
against the checkout root. A smarter regex is not the fix -- adding lookarounds
for quotes will fail on the next nesting case, and heredoc bodies are not
expressible as a regex exclusion at all.

CHECK FIRST, do not assume: read the guard's current matcher before rewriting
it. It may already tokenize and have one bad branch, in which case the change is
small -- but the fixture enumeration below still applies.

THE MORE IMPORTANT HALF -- DO NOT WEAKEN THE GUARD. This guard stops agents
dirtying the shared root, which DirtyMain-blocks every concurrent land and has
already deadlocked this fleet more than once. A fix that reduces false positives
by also letting real writes through is far worse than the bug it fixes. Treat
the must-fire set as the primary acceptance criterion.

MUST-FIRE FIXTURES (must still be refused):
  - a truncating redirect to a path inside the checkout
  - an appending redirect to a path inside the checkout
  - a redirect whose target comes from a variable holding a checkout path
  - tee writing into the checkout
  - a heredoc redirected INTO a checkout path
  - a relative-path redirect that resolves into the checkout

MUST-STAY-QUIET FIXTURES (must be allowed):
  - a numeric comparison operator inside single quotes
  - the same inside a double-quoted string
  - the same inside a heredoc body not itself targeting the checkout
  - a redirect whose target is under /tmp
  - a file-descriptor redirect
  - prose about redirection written to a file outside the checkout

ACCEPTANCE
- The current matcher read and quoted in the done report before any change.
- A tokenized decision, not a refined pattern.
- Both fixture sets committed. The must-fire set matters most: a guard that
  stops refusing real writes looks exactly like a guard that was fixed.
