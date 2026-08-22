---
id: T-2481
title: the root-write guard does not cover Bash, which is how all three root-dirtying
  incidents actually happened
state: done
kind: bug
origin: human
created: '2026-08-18'
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
- .claude/settings.json
- docs/guides/claude-hooks.md
evidence_scope:
- tests/test_hook_root_write_guard.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: .claude/settings.json
  reason: 'Extending root-write-guard.py to Bash requires wiring the matcher in

    .claude/settings.json (adding "Bash" alongside Write|Edit|NotebookEdit,

    or a separate hook entry) -- without it the new Bash-detection logic in

    root-write-guard.py never runs. Adding settings.json to scope.

    '
  actor: logan
  at: '2026-08-18'
- op: add
  glob: docs/guides/claude-hooks.md
  reason: 'frob:doc edges in root-write-guard.py point at docs/guides/claude-hooks.md

    (#root-write-guardpy); updating the guard''s Bash behavior requires updating

    that doc section in the same change to keep DRIFT001 clean.

    '
  actor: logan
  at: '2026-08-18'
evidence:
- tests/test_hook_root_write_guard.py::test_bash_ticket_verb_with_no_cd_no_path_no_marker_is_refused
- tests/test_hook_root_write_guard.py::test_bash_ticket_verb_with_cd_into_worktree_is_allowed
- tests/test_hook_root_write_guard.py::test_bash_ticket_verb_with_explicit_path_flag_is_allowed
- tests/test_hook_root_write_guard.py::test_bash_ticket_verb_with_coordinator_marker_is_allowed
- tests/test_hook_root_write_guard.py::test_bash_ambiguous_redirect_target_is_allowed
designated_repro_test: null
acceptance:
- text: Given an agent-context ticket-mutating command issued from the primary checkout
    with neither a cd into a worktree in the same call nor an explicit --path, when
    it runs, then it is refused before the root is dirtied.
  evidence:
  - tests/test_hook_root_write_guard.py::test_bash_ticket_verb_with_no_cd_no_path_no_marker_is_refused
- text: Given the same command with cd worktree in the same call or an explicit --path,
    when it runs, then it succeeds unchanged.
  evidence:
  - tests/test_hook_root_write_guard.py::test_bash_ticket_verb_with_cd_into_worktree_is_allowed
  - tests/test_hook_root_write_guard.py::test_bash_ticket_verb_with_explicit_path_flag_is_allowed
- text: Given the coordinator or a human running that command in the root, when it
    runs, then the guard does not fire, proving the discriminator works in both directions.
  evidence:
  - tests/test_hook_root_write_guard.py::test_bash_ticket_verb_with_coordinator_marker_is_allowed
- text: Given a Bash command whose write target cannot be determined, when it runs,
    then it is allowed rather than refused, so the guard cannot block legitimate work
    on a guess.
  evidence:
  - tests/test_hook_root_write_guard.py::test_bash_ambiguous_redirect_target_is_allowed
evidence_changes:
- old_node: tests/test_hook_root_write_guard.py::test_bash_ticket_verb_with_no_cd_and_no_path_is_refused
  new_node: tests/test_hook_root_write_guard.py::test_bash_ticket_verb_with_no_cd_no_path_no_marker_is_refused
  reason: T-2850 rewrote the guard's test suite for its default-inversion; old node
    id no longer resolves, re-pointed to the closest surviving test covering the same
    behavior class under the new contract
  actor: logan
  at: '2026-08-22'
- old_node: tests/test_hook_root_write_guard.py::test_bash_ticket_verb_from_human_or_coordinator_shell_is_allowed
  new_node: tests/test_hook_root_write_guard.py::test_bash_ticket_verb_with_coordinator_marker_is_allowed
  reason: T-2850 inverted the default this test's name described (human/coordinator
    with no markers is now DENIED, not allowed); re-pointed to the surviving positive
    control proving the explicit FROB_COORDINATOR marker still allows the write
  actor: logan
  at: '2026-08-22'
threat: null
component: hooks
anchor: false
anchor_reason: null
land_commit: 2e57980f29e6cb520b2eb7a95f4e835267d4a2d9
---
T-2396 installed an edit-time guard refusing agent writes to the shared
root. It is wired on `matcher: "Write|Edit|NotebookEdit"` and its
`_GUARDED_TOOLS` is `frozenset({"Write", "Edit", "NotebookEdit"})`. The
string `"Bash"` does not appear in the hook at all.

So a write performed through Bash -- a heredoc, a `>` redirect,
`sed -i`, `tee`, a python one-liner -- is completely unguarded.

MEASURED: THREE separate agents dirtied the shared root today, and ALL
THREE did it through Bash, not through the Edit tool:

  - one ran `frob ticket done-report` without a `cd <worktree> &&` in
    the same call; it wrote to the root's own copy of the ticket
  - one made its error-floor edits directly in the root (four files),
    DirtyMain-blocking T-2441 and, transitively, four more tickets
  - one omitted the `cd` prefix on `python3` heredoc calls and landed
    its first edit pass on the root checkout

Every one was caught late -- at land time, via a `DirtyMain` refusal --
which is exactly the "guard fires after the damage" problem T-2396 was
filed to fix. The guard shipped, works correctly for the tools it
covers, and did not fire once, because nobody was using those tools to
do it.

ROOT CAUSE OF THE MISS, worth stating because it generalises: the
harness RESETS CWD BETWEEN BASH CALLS. So a multi-call sequence that
`cd`s once and then issues commands assuming that directory silently
operates on the root instead. That is not an occasional slip; it is the
default failure mode of the interface, which is why three careful
agents hit it independently in one session.

FIX SHAPE:
  - Extend the guard to `Bash`. The hard part is that a Bash command's
    write TARGETS are not a declared field the way `Write`'s
    `file_path` is -- they must be inferred from the command text, and
    inference is exactly the lexical guessing this repo forbids
    elsewhere. So be conservative: do not attempt to parse arbitrary
    shell. Detect the narrow, high-frequency shapes actually observed
    (a `frob ticket <mutating-verb>` with neither a `cd` into a
    worktree in the same call nor an explicit `--path`; a `>`/`>>`/
    `tee`/`sed -i` whose target resolves under the primary checkout),
    and let anything ambiguous through rather than blocking work on a
    guess. A guard that blocks legitimate commands will be disabled,
    and then it protects nothing.
  - Preserve the existing discriminator work: fire only in agent
    context (the paired `FROB_AGENT` / registered-worktree fact check
    from T-2396, plus T-2412's fix so writes INSIDE a nested worktree
    are allowed), keep the `tickets/**` exemption, and keep honouring
    `FROB_LAND_INTERNAL`.
  - Consider the cheaper complementary fix as well or instead: have
    `frob`'s own ticket-mutating verbs refuse, or loudly warn, when
    invoked with cwd == the primary checkout while `FROB_AGENT` is set
    and the ticket has a live worktree. That puts the check inside the
    tool that knows the answer, rather than inferring it from shell
    text. It would have caught two of today's three cases outright.

POSITIVE CONTROLS:
  - must-now-refuse: an agent-context `frob ticket done-report` (or
    similar mutating verb) issued with no `cd` and no `--path`, from
    the primary checkout, is refused.
  - must-still-allow: the identical command with `cd <worktree> &&` in
    the same call, or with `--path <worktree>`, succeeds.
  - must-still-allow-human: the coordinator or a human running the same
    command in the root is unaffected -- verify both directions, since
    this repo has shipped a guard that never fired and a guard that
    always fired, and both were useless.
  - must-not-overblock: a Bash command whose write target cannot be
    determined is ALLOWED, not refused.