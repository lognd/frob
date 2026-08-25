---
id: T-draft-9122342b
title: 'Root-write guard: cwd-keyed target, dead FROB_COORDINATOR hatch, mis-scoped
  ledger exemption'
state: queued
kind: bug
origin: human
created: '2026-08-25'
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
  glob: docs/guides/claude-hooks.md
  reason: doc edges for touched symbols require this file in scope
  actor: logan
  at: '2026-08-25'
- op: add
  glob: docs/guides/claude-hooks.md
  reason: doc edges for touched symbols require this file in scope
  actor: logan
  at: '2026-08-25'
designated_repro_test: null
acceptance:
- text: Given a Bash write whose real target path lies entirely outside the primary
    checkout (e.g. under the user's home directory, home-relative shorthand), issued
    with the shell cwd at the primary checkout root, when the hook evaluates the call,
    then it must ALLOW the write (no denial), because the write's real target is not
    the primary checkout.
  evidence: []
- text: Given a Bash write whose real target path lies inside the primary checkout,
    issued from an agent shell with no worktree cd and no ledger-only ticket verb
    involved, when the hook evaluates the call, then it must still DENY the write
    -- the guard must not be weakened for genuine root writes.
  evidence: []
- text: Given the coordinator opt-in marker is enabled via the hook's supported persistence
    mechanism (a file the hook reads from disk, not a process environment variable),
    when a write targeting the primary checkout is evaluated, then it must be ALLOWED,
    and the mechanism must actually work end-to-end as a real PreToolUse-hook-process
    check, not merely as an env var passed to the Bash tool's own subprocess.
  evidence: []
- text: Given the ledger-only mutating ticket verbs, when invoked via Bash from the
    primary checkout root with no cd into a worktree, then they must be ALLOWED (matching
    the documented "tickets.md/tickets/** are exempt" claim), while the "land" verb
    without a --worktree flag naming a real registered worktree must still be DENIED.
  evidence: []
- text: Given the refusal message text, when read by an operator, then every escape
    hatch and exemption it names must actually function as described -- no documented
    hatch that does not work.
  evidence: []
threat: null
component: hooks
anchor: false
anchor_reason: null
land_commit: null
---
The T-2850 shared-root write guard (.claude/hooks/root-write-guard.py)
has three measured defects, each reproduced directly against the hook's
real stdin/stdout contract (not just theorized):

1. Path-target resolution treats a "~"-prefixed path as RELATIVE, not
   absolute. os.path.isabs("~/foo") is False, so
   _resolve_relative/_unambiguous_target join it onto the effective cwd
   instead of expanding it, and a Bash write whose real target is
   entirely outside the repo (e.g. a heredoc into a path under the
   user's home directory, memory notes for example) falsely resolves
   under the primary checkout and is refused, purely because the
   shell's cwd is the repo root. The identical command with a leading
   cd into /tmp succeeds, confirming the false refusal is about cwd,
   not the real target.

2. FROB_COORDINATOR=1 does not lift the guard in real usage, though the
   refusal text advertises it as the "genuine coordinator/human shell"
   escape hatch. Root cause: the PreToolUse hook runs as a process
   spawned directly by the harness per .claude/settings.json, which
   never inherits env vars a not-yet-executed Bash command would
   export -- there is no process relationship through which an export
   inside one Bash tool call could ever reach the hook's own env. An
   env-var marker structurally cannot work for this hook; only a
   persistent state file the hook can read from disk before the tool
   call is even a candidate.

3. The advertised ledger exemption does not apply to a mutating
   ticket-verb invocation run via Bash from the root -- the CLI's own
   "new" subcommand (and every other ledger-only mutating verb except
   land) is refused outright. The Bash-shape detector infers only the
   command's effective CWD, never the actual file the CLI subprocess
   will write, so it cannot apply the same ledger exemption already
   given to the Write/Edit tool path. Message and behavior disagree.

Fix must NARROW the guard to writes whose real target is the primary
checkout -- never weaken it into general permissiveness. A write
genuinely targeting the primary checkout from an agent shell must still
be refused after the fix.
