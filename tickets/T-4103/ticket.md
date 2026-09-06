---
id: T-4103
title: the first SUITE-RESULT line shares a line with pytest's [100%] progress output,
  so the repo's own always-greppable signal cannot be anchored
state: in-progress
kind: bug
origin: agent
created: '2026-09-06'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/conftest.py
- tests/unit/test_conftest_stackdump.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given pytest progress output that ended mid-line, when pytest_sessionfinish
    writes the SUITE-RESULT line, then that text begins at column zero and matches
    a ^-anchored grep
  evidence: []
- text: given a terminal already at column zero, when the SUITE-RESULT line is written,
    then the output is byte-for-byte identical to before this change
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
THE FIRST `SUITE-RESULT:` LINE SHARES A LINE WITH PYTEST'S `[100%]` PROGRESS
OUTPUT, so the one line every consumer greps for is not at the start of a line.
Reported three times by the repo owner off real CI logs, most recently against
the third complete Windows run:

    ......................[100%]SUITE-RESULT: exitstatus=1 collected=13494 failed=19

THE MECHANISM IS ALREADY DOCUMENTED IN THE REPO, which is why this is a fix and
not an investigation. `.github/workflows/ci.yml:234` carries a T-3531 comment
stating it verbatim: pytest's `-q` progress output ends WITHOUT a newline, and
`tests/conftest.py`'s `pytest_sessionfinish` then calls
`reporter.write_line(line)`, which appends to whatever column the terminal is
already at. That workflow WORKED AROUND it by dropping the `^` anchor from its
grep and using `-o` to extract the matched suffix.

A WORKAROUND IN ONE CONSUMER IS NOT A FIX, and this is the wrong-incentive shape
the queue keeps finding: the producer emits a malformed line, and each consumer
pays for it separately and silently. The `SUITE-RESULT:` line's entire purpose
(T-1596) is to be an always-greppable "the run actually finished" signal that
survives any verbosity stacking. A signal that cannot be `^`-anchored is a
weaker signal than the docstring promises, and every future reader -- human or
script -- has to learn the exception first. The repo owner has now had to report
it three times, which is the cost being measured.

THE FIX IS ONE CALL, and pytest provides exactly the right primitive:
`TerminalReporter.ensure_newline()` writes a newline only if the terminal is not
already at column zero. Call it once before the first `write_line` in
`pytest_sessionfinish` (verified present on the pinned pytest 9.0.3). Because it
is a no-op when already at line start, a run whose progress output DID end in a
newline is byte-for-byte unchanged -- no blank line appears.

DO NOT `write_line("")` INSTEAD. That unconditionally emits a blank line, which
changes the output of every run that was already correct, and would disturb the
deliberately-pinned completed-run format.

WHAT TO CHECK BEYOND THE ONE CALL
  - `tests/unit/test_conftest_stackdump.py` pins the completed-run line format.
    The fix changes what precedes the line, not the line, so that pin should
    hold -- confirm it does rather than assuming.
  - `src/frob/gates/_bug_repro.py:894` regex-matches `\bcollected=0\b` against
    this line (T-2025). Unaffected, but named here so the next editor knows the
    line has a second consumer.
  - Once the producer is correct, the ci.yml T-3531 workaround may be
    simplified. DO NOT simplify it in this ticket: the workflow must keep
    matching logs produced by OLDER commits during any bisect or rerun. Leave
    the comment and the `-o` grep in place, and note in the comment that the
    producer now emits a leading newline.

MUST-FIRE FIXTURE:   with the terminal mid-line (progress output written with no
                     trailing newline), the emitted `SUITE-RESULT:` text starts
                     at column zero and `^SUITE-RESULT` matches it.
MUST-STAY-QUIET:     with the terminal already at column zero, the output is
                     byte-for-byte identical to today -- no inserted blank line.
THIRD FIXTURE:       the completed-run line format pinned by
                     test_conftest_stackdump.py still passes unchanged.

ACCEPTANCE
- `ensure_newline()` called once before the first SUITE-RESULT write.
- No blank line introduced on an already-newline-terminated run.
- The ci.yml workaround left intact, with its comment updated to record that the
  producer is now fixed and the loose grep is retained for old logs.
- All three fixtures committed.
