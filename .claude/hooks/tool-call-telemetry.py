"""PreToolUse/PostToolUse hooks: record one `kind="tool"` telemetry event
per Claude Code tool call (T-2912).

WHY THIS EXISTS. `frob.stats._agentic.dispatch_cost_report` (T-1724) and
`agentic_report`'s `tool_tokens` field have both read `kind="tool"` events
since they were built, but no caller ever wrote one -- T-1724 shipped the
join logic and deliberately left the write side unwired. Every per-agent
cost number this repo has published (the 1,446-tokens-per-call figure
behind T-2909/T-2908) came from hand-tallying a session transcript, not
from this stream. This hook is the missing write side: it turns "how many
tool calls, of what shape, cost how much" from a one-off manual count into
something `frob stats --agentic` answers automatically, every session,
without anyone remembering to run a command for it (the standing
"automatic over commands" directive -- see MEMORY.md).

REUSES THE EXISTING STREAM, ON PURPOSE. This does not start a second
telemetry file or a second event shape: it appends to the SAME
`.frob/telemetry.jsonl` `record_cli_event`/`record_dispatch_event` already
write, using the EXACT `kind="tool"` field names (`tool`,
`output_tokens_est`) `_tool_tokens`/`_dispatch_records` in
`frob.stats._agentic` already read. Two independently-evolving telemetry
systems is exactly the duplication this repo's engineering principles
forbid (NO DUPLICATION).

NO `frob` IMPORT, DELIBERATELY -- same constraint as `dispatch-telemetry.py`
(Claude Code invokes hooks with the system `python3`, commonly older than
the 3.11+ `frob` itself requires). This script re-derives the tiny handful
of primitives it needs (iso timestamp, JSON-line append, a redaction-safe
command shape) directly with the stdlib rather than importing `frob`.

PRIVACY: NEVER RECORD RAW COMMAND TEXT. A `Bash` tool call's `command`
field can carry secrets, tokens, or file contents pasted inline. This
script never writes that string. For `Bash` it writes a `command_shape`:
the first pipeline segment's verb plus its bare flag tokens only (`-x`,
`--foo`), lexically filtered to exclude anything that looks like it carries
a value (`--foo=bar`, a quoted string, a path, a number) -- ambiguous
tokens are dropped, never guessed-and-kept. For every other tool
(`Read`/`Edit`/`Write`/`Grep`/...) only the tool name is recorded; no
attempt is made to shape-normalize their arguments, since a file path is
already more identifying than a flag name and "capture less" is this
ticket's explicit fallback instruction when safe normalization is not
possible.

OVERHEAD. This hook fires on EVERY tool call in EVERY session, an order of
magnitude more often than `record_cli_event` (Bash-invoked `frob`
subcommands only). It deliberately does ZERO subprocess spawns per event
-- no `git rev-parse`, no `frob` invocation. Tree-state identity
(`head_sha`) is read by parsing `.git`/`HEAD`/packed-refs files directly
(`_fast_head_sha`), the same identity `frob.app.telemetry.tree_hash` uses
(short HEAD sha) but without paying a process spawn for it on the hot
path. Measured overhead is reported in T-2912's Done report.

TESTED FROM `tests/test_hook_dispatch_telemetry.py`, NOT ITS OWN FILE. That
file's `testsuite` node is already named in `design/frob.strata`'s `may
"exec" via ...` allowlist for `dispatch-telemetry.py`'s own subprocess
tests; folding this hook's tests in there (rather than a new
`tests/test_hook_tool_call_telemetry.py`) avoided needing to edit that
same strata file, which was under a live cross-worktree lease (T-2911) at
this ticket's own land time.

TWO PHASES, ONE JOIN KEY. `PreToolUse` records `phase="pre"` (an attempt --
recorded even if a LATER hook in the chain blocks the call and it never
actually runs); `PostToolUse` records `phase="post"` (a completed call,
with `output_tokens_est`). Both carry the same `dispatch_id` (session_id,
matching `dispatch-telemetry.py`'s own join key) plus `tool` and
`command_shape`. A `phase="pre"` event with no matching `phase="post"`
event before the NEXT `phase="pre"` event is a call that was blocked (by a
PreToolUse hook denial) or otherwise never completed -- this repo already
knows land cost is dominated by refusals, not timeouts, and this is the
general-purpose version of that same measurement. Correlating pre/post
pairs is left to the reporting layer (`frob.stats._agentic`), not baked
into this hook, so the hook itself stays a single cheap append with no
in-memory state to get wrong across process boundaries (every tool call is
a fresh `python3` invocation of this script).

TELEMETRY OPT-OUT: respects `FROB_NO_TELEMETRY`, same env var and
truthiness rule as `frob.app.telemetry.is_disabled`, matching
`dispatch-telemetry.py`'s own precedent.

NEVER BLOCKS. Every write is best-effort; any failure is swallowed and the
hook exits 0 silently, same posture as `dispatch-telemetry.py`.
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# Recognized standalone-flag shape: `-x`, `--foo`, `--foo-bar`. Anything with
# an `=`, a quote, a `/`, or a digit-only body is assumed to carry a VALUE
# (a path, a number, an inline secret) and is dropped, never kept partially.
_FLAG_RE = re.compile(r"^-{1,2}[A-Za-z][A-Za-z0-9-]*$")

# A "chain word" extends the verb (`uv run pytest`, `git ticket land`) --
# purely alphabetic/hyphenated with NO digits, so a ticket id, a version
# string, or any other value-shaped token ends the chain instead of
# leaking into the shape.
_CHAIN_WORD_RE = re.compile(r"^[A-Za-z][A-Za-z-]*$")

# Shell metacharacters that end the FIRST pipeline segment of a compound
# command -- only that first segment's verb+flags are ever recorded, never
# anything after a `&&`/`;`/`|`/backtick/`$(`.
_SEGMENT_END_RE = re.compile(r"&&|;|\||`|\$\(")

_MAX_SHAPE_TOKENS = 12
"""Cap on flag tokens kept per command shape -- a runaway or adversarial
command line must not grow an unbounded telemetry record."""


def _telemetry_disabled() -> bool:
    """Mirrors `frob.app.telemetry.is_disabled` exactly, without importing
    `frob` -- see the module docstring's "NO `frob` IMPORT" note."""
    # frob:waive SEC110 reason="opt-out flag, not a secret"
    value = os.environ.get("FROB_NO_TELEMETRY", "")
    return value.strip().lower() not in ("", "0", "false")


def _iso_now() -> str:
    """Mirrors `frob.app.telemetry.iso_now`'s exact format so a hook-written
    record is byte-for-byte indistinguishable in shape from one the
    library itself writes."""
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


# frob:waive DUP001 reason="matches dispatch-telemetry.py's and diagnosis-nudge.py's \
# own identical _repo_root -- each standalone hook script is deliberately self- \
# contained (NO frob import, per this file's own module docstring) so it cannot break \
# if Claude Code invokes it with a bare system python3; extracting a shared helper \
# module would reintroduce exactly the import-availability risk this duplication \
# exists to avoid"
def _repo_root(cwd: str) -> Path | None:
    """Nearest ancestor of `cwd` containing `.git`, or `None` outside a git
    repo -- mirrors `dispatch-telemetry.py`'s own helper."""
    here = Path(cwd).resolve() if cwd else Path.cwd()
    for candidate in (here, *here.parents):
        if (candidate / ".git").exists():
            return candidate
    return None


def _resolve_gitdir(root: Path) -> Path | None:
    """`root`'s real git directory: `root/.git` itself for a normal
    checkout, or the target of `root/.git`'s `gitdir: <path>` pointer for a
    linked worktree (every dispatch worktree in this repo). No subprocess:
    this is a single small-file read, unlike `frob.app.telemetry.tree_hash`
    which spawns `git rev-parse` -- see the module docstring's OVERHEAD
    note for why that distinction matters on this hot a path."""
    dotgit = root / ".git"
    if dotgit.is_dir():
        return dotgit
    if dotgit.is_file():
        try:
            text = dotgit.read_text(encoding="utf-8", errors="replace").strip()
        except OSError:
            return None
        if text.startswith("gitdir:"):
            target = Path(text.split(":", 1)[1].strip())
            if not target.is_absolute():
                target = (root / target).resolve()
            return target
    return None


def _fast_head_sha(root: Path) -> str:
    """Short (7-char) HEAD sha for `root`, or `"unknown"` -- read directly
    from `.git`/`HEAD` and the ref file it points at, with ZERO subprocess
    spawns (deliberately cheaper than `frob.app.telemetry.tree_hash`, which
    is fine to spawn `git` at `frob` CLI-invocation frequency but not at
    every-tool-call frequency). Falls back to `"unknown"` rather than
    guessing whenever the ref cannot be resolved this way (a detached HEAD
    written as a raw sha is handled directly; a packed ref falls back to
    `"unknown"` rather than parsing `packed-refs` -- capturing less is
    preferred over a wrong shape here, matching the ticket's own privacy
    fallback instruction)."""
    gitdir = _resolve_gitdir(root)
    if gitdir is None:
        return "unknown"
    head_path = gitdir / "HEAD"
    try:
        head_text = head_path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return "unknown"
    if head_text.startswith("ref:"):
        ref = head_text.split(":", 1)[1].strip()
        ref_path = gitdir / ref
        try:
            sha = ref_path.read_text(encoding="utf-8", errors="replace").strip()
        except OSError:
            return "unknown"
    else:
        sha = head_text
    if len(sha) < 7 or not re.fullmatch(r"[0-9a-fA-F]+", sha):
        return "unknown"
    return sha[:7]


def _bash_command_shape(command: str) -> str | None:
    """Normalize a `Bash` tool call's `command` string to `"<verb> <chain
    word> ... <flag1> <flag2> ..."` -- the first pipeline segment's leading
    word, EXTENDED through any immediately-following bare subcommand words
    (`uv run pytest` stays distinguishable from `uv run frob`, rather than
    both collapsing to just `uv` -- T-2912's own real-histogram run
    surfaced that flatter shape as too coarse to be useful), plus any bare
    flag-shaped tokens anywhere in the segment, sorted for stability.
    A "chain word" is a purely-alphabetic hyphenated token with NO digits
    (`_CHAIN_WORD_RE`) -- a ticket id (`T-2912`), a file path, or any other
    value-shaped token ends the chain (but flags after it are still
    collected), so shapes stay generic across different tickets/paths
    rather than leaking an identifier into the aggregate. Never includes
    argument values, quoted text, or literal file content. Returns `None`
    if no safe verb can be extracted (e.g. an empty/whitespace command)."""
    segment_match = _SEGMENT_END_RE.search(command)
    segment = command[: segment_match.start()] if segment_match else command
    tokens = segment.split()
    if not tokens:
        return None
    verb = tokens[0]
    if not re.fullmatch(r"[A-Za-z0-9_./-]+", verb):
        # The "verb" position itself looks like a variable expansion, quote,
        # or redirection -- too ambiguous to record safely; capture less.
        return "<unrecognized>"
    chain = [verb]
    flags: set[str] = set()
    chain_ended = False
    for tok in tokens[1:]:
        if _FLAG_RE.match(tok):
            flags.add(tok)
        elif not chain_ended and _CHAIN_WORD_RE.match(tok):
            chain.append(tok)
        else:
            chain_ended = True
    ordered_flags = sorted(flags)[:_MAX_SHAPE_TOKENS]
    return " ".join([*chain, *ordered_flags])


def _output_tokens_est(tool_response: object) -> int:
    """Rough `len(text) / 4` estimate of a tool response's size, mirroring
    `frob.app.telemetry.estimate_tokens`'s exact heuristic (re-derived here
    per the module docstring's "NO `frob` IMPORT" constraint) -- ranks
    tools by cumulative output size, not an exact tokenizer count."""
    text = json.dumps(tool_response, sort_keys=True) if tool_response else ""
    return max(0, len(text) // 4)


# frob:waive DUP001 reason="matches dispatch-telemetry.py's own _append_dispatch_event \
# -- same standalone-hook-script self-containment constraint as _repo_root above (NO \
# frob import), not worth a shared helper module for a 6-line best-effort JSON-line \
# append"
def _append_tool_event(root: Path, record: dict) -> None:
    """Append one `kind="tool"` JSON line to `root/.frob/telemetry.jsonl`,
    the exact shape `frob.stats._agentic` already reads. Best-effort: any
    I/O failure is swallowed."""
    if _telemetry_disabled():
        return
    path = root / ".frob" / "telemetry.jsonl"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, sort_keys=True))
            fh.write("\n")
    except OSError:
        pass


def _build_record(payload: dict, *, phase: str, root: Path) -> dict:
    """Shared record shape for both phases -- only `phase="post"` adds
    `output_tokens_est` (there is no response to size at `phase="pre"`)."""
    tool = str(payload.get("tool_name", "unknown"))
    tool_input = payload.get("tool_input")
    command_shape = None
    if tool == "Bash" and isinstance(tool_input, dict):
        command = tool_input.get("command")
        if isinstance(command, str):
            command_shape = _bash_command_shape(command)
    record: dict = {
        "iso_ts": _iso_now(),
        "kind": "tool",
        "dispatch_id": str(payload.get("session_id", "unknown")),
        "tool": tool,
        "phase": phase,
        "head_sha": _fast_head_sha(root),
    }
    if command_shape is not None:
        record["command_shape"] = command_shape
    return record


def _handle_pre(payload: dict, root: Path) -> None:
    """Record `phase="pre"`: an attempted tool call, whether or not it
    goes on to actually execute."""
    _append_tool_event(root, _build_record(payload, phase="pre", root=root))


def _handle_post(payload: dict, root: Path) -> None:
    """Record `phase="post"`: a completed tool call, with
    `output_tokens_est` sized from `tool_response`."""
    record = _build_record(payload, phase="post", root=root)
    record["output_tokens_est"] = _output_tokens_est(payload.get("tool_response"))
    _append_tool_event(root, record)


def _parse_stdin_payload(raw: str) -> dict | None:
    """`raw`'s stdin text parsed as a JSON object, or `None` for anything
    else -- matches `dispatch-telemetry.py`'s own parser."""
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except ValueError:
        return None
    return payload if isinstance(payload, dict) else None


def _dispatch_event(payload: dict, root: Path) -> None:
    """Routes `payload` to `_handle_pre`/`_handle_post` by its
    `hook_event_name`; anything else is a silent no-op."""
    event_name = payload.get("hook_event_name")
    if event_name == "PreToolUse":
        _handle_pre(payload, root)
    elif event_name == "PostToolUse":
        _handle_post(payload, root)


def _process_stdin(raw: str) -> None:
    """Parses `raw` and, if it names a resolvable repo root, hands it to
    `_dispatch_event`; an unparseable payload or an unresolvable root is a
    silent no-op. Split out of `main` so the entry point itself stays a
    single unconditional call with no branching of its own."""
    payload = _parse_stdin_payload(raw)
    root = _repo_root(str(payload.get("cwd", ""))) if payload is not None else None
    if payload is not None and root is not None:
        _dispatch_event(payload, root)


# frob:doc docs/guides/agentic-time-profiling.md#tool-call-telemetry-t-2912
# frob:tests tests/test_hook_dispatch_telemetry.py::test_pre_tool_use_records_attempt_event kind="integration"  # noqa: E501
# frob:tests tests/test_hook_dispatch_telemetry.py::test_post_tool_use_records_completion_with_token_estimate kind="integration"  # noqa: E501
def main() -> int:
    """Entry point: hands the stdin JSON payload to `_process_stdin`.
    Always exits 0 -- a telemetry hook must never block or fail a tool
    call."""
    _process_stdin(sys.stdin.read())
    return 0


if __name__ == "__main__":
    sys.exit(main())
