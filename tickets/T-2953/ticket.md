---
id: T-2953
title: 'Windows: natives build crashes with UnicodeDecodeError decoding maturin subprocess
  output (cp1252)'
state: done
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
- src/frob/serve/_socketd.py
- src/frob/app/_daemon_proxy.py
- src/frob/app/ticket_runner/_land_cmd.py
- src/frob/app/ticket_runner/_close_cmd.py
- src/frob/app/ticket_runner/_rapid_sweep.py
- tests/unit/test_process_guard.py
- docs/modules/process.md
- docs/modules/serve.md
- tickets/T-2961/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/serve/_socketd.py
  reason: 'The class sweep (subprocess.run/Popen with text=True/universal_newlines=True

    and no explicit encoding=) found 5 raw call sites outside

    guarded_subprocess_run''s own seam; fixing the class (per coordinator

    directive, not just the one call site in the traceback) requires

    touching all of them plus their regression test file.

    '
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/app/_daemon_proxy.py
  reason: 'The class sweep (subprocess.run/Popen with text=True/universal_newlines=True

    and no explicit encoding=) found 5 raw call sites outside

    guarded_subprocess_run''s own seam; fixing the class (per coordinator

    directive, not just the one call site in the traceback) requires

    touching all of them plus their regression test file.

    '
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/app/ticket_runner/_land_cmd.py
  reason: 'The class sweep (subprocess.run/Popen with text=True/universal_newlines=True

    and no explicit encoding=) found 5 raw call sites outside

    guarded_subprocess_run''s own seam; fixing the class (per coordinator

    directive, not just the one call site in the traceback) requires

    touching all of them plus their regression test file.

    '
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/app/ticket_runner/_close_cmd.py
  reason: 'The class sweep (subprocess.run/Popen with text=True/universal_newlines=True

    and no explicit encoding=) found 5 raw call sites outside

    guarded_subprocess_run''s own seam; fixing the class (per coordinator

    directive, not just the one call site in the traceback) requires

    touching all of them plus their regression test file.

    '
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/app/ticket_runner/_rapid_sweep.py
  reason: 'The class sweep (subprocess.run/Popen with text=True/universal_newlines=True

    and no explicit encoding=) found 5 raw call sites outside

    guarded_subprocess_run''s own seam; fixing the class (per coordinator

    directive, not just the one call site in the traceback) requires

    touching all of them plus their regression test file.

    '
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tests/unit/test_process_guard.py
  reason: 'The class sweep (subprocess.run/Popen with text=True/universal_newlines=True

    and no explicit encoding=) found 5 raw call sites outside

    guarded_subprocess_run''s own seam; fixing the class (per coordinator

    directive, not just the one call site in the traceback) requires

    touching all of them plus their regression test file.

    '
  actor: logan
  at: '2026-08-26'
- op: add
  glob: docs/modules/process.md
  reason: 'AFFECT001 closure for guarded_subprocess_run (docs/modules/process.md)

    and _source_head_sha (docs/modules/serve.md), plus the T-draft ticket

    filed for the ty-check POSIX-only-stdlib-attrs defect discovered while

    getting a real windows-latest CI run past the subprocess decode class.

    '
  actor: logan
  at: '2026-08-26'
- op: add
  glob: docs/modules/serve.md
  reason: 'AFFECT001 closure for guarded_subprocess_run (docs/modules/process.md)

    and _source_head_sha (docs/modules/serve.md), plus the T-draft ticket

    filed for the ty-check POSIX-only-stdlib-attrs defect discovered while

    getting a real windows-latest CI run past the subprocess decode class.

    '
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tickets/T-2961/**
  reason: 'AFFECT001 closure for guarded_subprocess_run (docs/modules/process.md)

    and _source_head_sha (docs/modules/serve.md), plus the T-draft ticket

    filed for the ty-check POSIX-only-stdlib-attrs defect discovered while

    getting a real windows-latest CI run past the subprocess decode class.

    '
  actor: logan
  at: '2026-08-26'
evidence:
- tests/unit/test_process_guard.py::TestDefaultTextEncoding::test_injects_utf8_replace_when_text_true_and_no_encoding
- tests/unit/test_process_guard.py::TestDefaultTextEncoding::test_injects_when_universal_newlines_true
- tests/unit/test_process_guard.py::TestDefaultTextEncoding::test_never_overrides_explicit_encoding
- tests/unit/test_process_guard.py::TestDefaultTextEncoding::test_never_overrides_explicit_errors
- tests/unit/test_process_guard.py::TestDefaultTextEncoding::test_no_op_without_text_mode
- tests/unit/test_process_guard.py::TestDefaultTextEncoding::test_guarded_subprocess_run_survives_the_reported_crash_byte
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