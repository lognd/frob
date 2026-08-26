---
id: T-draft-3923b7dc
title: 'Windows: natives build crashes with UnicodeDecodeError decoding maturin subprocess
  output (cp1252)'
state: queued
kind: bug
origin: human
created: '2026-08-26'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/process/_guard.py
- src/frob/natives/_build.py
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
MEASURED via a real windows-latest CI run on T-2952's PR
(https://github.com/lognd/frob/pull/2, run 32938258727, job
98083729311), after T-2952 fixed the three bare `import fcntl` sites.

frob now IMPORTS successfully on Windows -- the whole import chain
(uv sync, uv run frob natives build's own frob import) completes with
no ModuleNotFoundError. That crash class is gone.

The NEXT crash in the same job is a different, unrelated bug:
`make core` (uv run frob natives build) crashes while building the
Rust extension via maturin, with:

  Exception in thread Thread-3 (_readerthread):
  ...
  File "...\subprocess.py", line 1599, in _readerthread
    buffer.append(fh.read())
  UnicodeDecodeError: 'charmap' codec can't decode byte 0x8f in
  position 2: character maps to <undefined>
  ERROR: main: unhandled exception during dispatch: 1 validation error
  for CrateBuildResult
  stdout
    Input should be a valid string [type=string_type, input_value=None,
    input_type=NoneType]

Root cause (not yet fixed, just localized): the maturin subprocess is
launched via `frob.process._guard.guarded_subprocess_run` (called from
`src/frob/natives/_build.py:239`), which reads the child's stdout as
text without an explicit `encoding=`/`errors=` -- Python's subprocess
module falls back to the platform's default codec (cp1252 on Windows,
not UTF-8), and cargo/maturin's real build output contains a byte
sequence cp1252 cannot decode (0x8f). The read raises inside a reader
thread, `stdout` ends up `None` on the result, and `CrateBuildResult`
(a pydantic model requiring `stdout: str`) then fails validation with
an unhandled exception instead of a clean error -- `make core` (the
FIRST step of every CI job and every worktree warm-up on this repo)
never completes on Windows.

This blocks `frob natives build`, which blocks every downstream
Windows CI job (build (windows-latest) and, transitively, any Windows
worktree/dev workflow that runs `make core` -- docs/guides/
agent-playbook.md section 1, item 2).

Suggested fix shape: `guarded_subprocess_run` (and/or its
subprocess.run/Popen call sites) should decode child output as UTF-8
with `errors="replace"` (or pass `encoding="utf-8"` explicitly)
instead of relying on the platform locale codec -- this is a general
"decode subprocess output portably" fix, not specific to maturin.

Filed per T-2952's own directive: "when you find [the next crash],
that is success, not failure: file it and report it." T-2952 remains
scoped to the three fcntl import sites; this is a new, unrelated
defect discovered only by getting past those three.

Acceptance: a real windows-latest CI run gets past `make core`
(`uv run frob natives build`) without a UnicodeDecodeError or a
CrateBuildResult validation error.
