---
id: T-3924
title: the protect-secrets hook blocks commands that MENTION a protected filename
  rather than commands that read one
state: queued
kind: bug
origin: human
created: '2026-09-05'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
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
The global protect-secrets hook blocks commands that MENTION the protected
substring rather than commands that READ protected material. Reported as
logand.app-v2 F-132 ("blocks `frob ticket new` when the title or body contains
the substring"), and REPRODUCED ON MYSELF TWICE while investigating it.

REPRODUCTION, 2026-09-05, unintentional and immediate: I ran a grep over the
hook's OWN SOURCE to inspect its matching, with the protected substring as part
of the grep PATTERN. Blocked:

    BLOCKED: command reads globally protected secret material
             (.env or SSH private key)

The command read a Python file in ~/.claude/hooks/. It read no protected
material. It could not have: the substring was a regex argument, not a path.
I could only inspect the hook by rewording the pattern to avoid naming what the
hook protects.

THE MECHANISM, from the hook's own source:

    hooks/protect-secrets.py, Bash branch
        cmd = strip_heredoc_bodies(ti.get("command", ""))
        m = BASH_READ_RE.search(cmd)
        if m and not ENV_TEMPLATE_RE.search(m.group()):
            block(...)

It SEARCHES THE WHOLE COMMAND STRING for a reader-verb-plus-protected-name
pattern. It does not determine whether that name is a PATH BEING READ, a
pattern argument, a ticket title, or prose. Three cases collapse into one:

    cat <protected>                     a real read          MUST block
    grep '<protected>' other_file.py    a search FOR the name MUST NOT block
    frob ticket new --title "...<name>..."  not a read at all MUST NOT block

THE NO-EXIT CONSEQUENCE, and it is the sharpest version of a shape found six
other times today: TO REPORT A PROBLEM WITH THIS HOOK YOU MUST NAME WHAT IT
PROTECTS, AND NAMING IT IS BLOCKED. A consumer cannot file a ticket about
protected-file handling. I could not grep the hook that was blocking me. The
guard forbids the discussion of itself.

THIS IS THE SEVENTH LEXICAL-MATCHING HOOK DEFECT TODAY. The other six are
frob-suggest's (hand-rename-sed firing on any sed-shaped text including a CRLF
strip and a markdown edit; the ack being line-anchored while the trigger scan is
not; the retry re-blocked when only trailing args differ; handrolled-floor-count
blocking a --help pipe and a worktree status line) plus the root-write guard
reading a quoted comparison operator as a redirect. Same root every time:
DECIDING ON SUBSTRING PRESENCE INSTEAD OF ON PARSED TOKENS AND WHAT THE COMMAND
ACTUALLY TOUCHES.

THE CONSTRAINT THAT OUTRANKS THE FIX -- READ THIS BEFORE CHANGING ANYTHING. The
owner's standing rule is absolute: NEVER read protected files, directly or
indirectly, including via shell expansion. This hook is the enforcement of a
rule I am not permitted to weaken, and I have relied on it. A change that
reduces false positives by letting ONE real read through is far worse than the
friction it fixes. The must-fire fixtures are the acceptance criterion; the
must-stay-quiet ones are the nice-to-have.

MUST-FIRE FIXTURES (every one must still block):
  - a direct read of a protected file by each reader verb in BASH_READ_RE
  - a read via a variable holding the path
  - a read inside a heredoc body that is itself redirected from the file
  - a read via a glob that expands to it
  - an indirect read through a subshell or command substitution
MUST-STAY-QUIET FIXTURES:
  - a grep whose PATTERN contains the name, over an unrelated file
  - a ticket verb whose title or body contains the name
  - prose in an editor/Write payload mentioning it
  - the documented template exemption, unchanged

FIX DIRECTION: parse the command, resolve which arguments are PATHS being read
by the matched verb, and decide on those. Where the parse is ambiguous, BLOCK --
this is the one hook where failing closed is correct, and that asymmetry should
be stated in the code so a later reader does not "improve" it into failing open.

DO NOT fix this by exempting `frob ticket` verbs by name. That is a denylist
wearing different clothes and it would not have unblocked my grep.
