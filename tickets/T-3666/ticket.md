---
id: T-3666
title: 'win32: conftest _write fixture converts LF to CRLF'
state: in-progress
kind: bug
origin: human
created: '2026-09-01'
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
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/gates_suite/test_fix_engine.py::TestFixEngineTierA::test_pre_fix_dirty_snapshot_captures_uncommitted_content
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Windows CI run 33521416410 (tracked by T-3659): two tests fail with a byte-for-byte CRLF-vs-LF mismatch on win32 only:
- tests/gates_suite/test_fix_engine.py::TestFixEngineTierA::test_pre_fix_dirty_snapshot_captures_uncommitted_content -- expects snapshot["dirty.py"] == b"uncommitted edit\n", gets b"uncommitted edit\r\n"
- tests/gates_suite/test_fix_engine.py::TestFixEngineTierA::test_before_snapshot_excludes_litmus_like_the_live_tree -- same shape, b"...\r\n" at byte index 28 where b"...\n" was expected

Root cause: tests/conftest.py's `_write(root, rel, text)` helper does `path.write_text(text)` with no `newline=` argument. Python's text-mode write with the default `newline=None` translates every `\n` in `text` to `os.linesep` on write -- on Windows that is `\r\n`. The test fixtures pass literal `\n`-only strings (e.g. `"uncommitted edit\n"`) expecting the file to contain exactly those bytes, but on win32 `_write` silently rewrites them to `\r\n` before the product code (the dirty-snapshot capture under test) ever reads the file back as raw bytes -- so the product code is reading the ACTUAL on-disk bytes correctly; the fixture is what introduced the CRLF.

This is out of my declared scope (tests/conftest.py is explicitly reserved for a sibling agent in this campaign) so I am filing it rather than fixing it directly.

Fix direction: `tests/conftest.py::_write` should open in a way that preserves the caller's literal newline bytes on every platform -- either `path.write_text(text, newline="")` (writes each `\n` verbatim, no translation) or `path.write_bytes(text.encode("utf-8"))`. Whichever is chosen should not change behavior for any of `_write`'s many existing POSIX-passing callers (POSIX's `os.linesep` is already `\n`, so `newline=""` is a no-op there).

Note for whoever picks this up: even after this fixture fix, real Windows checkouts of this repo (via git with core.autocrlf) can still legitimately produce CRLF-containing files on disk from a genuine `git clone`/`checkout`, independent of any test fixture -- so it may also be worth checking whether the dirty-snapshot/fix-engine consumers of this raw-byte content should normalize newlines themselves before comparing, separately from this fixture bug. Flagging as a related but distinct concern, not filing a second ticket for it without more evidence it is a live product-facing problem outside these two tests.

Traceback evidence: scratchpad/win-33521-failures.txt lines 1123-2225 (test_pre_fix_dirty_snapshot) and lines 4441-5553 (test_before_snapshot_excludes_litmus).

References T-3659 (tracking ticket for this campaign).
