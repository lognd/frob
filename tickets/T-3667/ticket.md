---
id: T-3667
title: 'win32: protocol_summary_gate finds zero violations (symref mismatch, unconfirmed)'
state: queued
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
- src/frob/graph/callgraph.py
- src/frob/graph/summary.py
- src/frob/gates/_protocol_summary.py
- src/frob/lang/__init__.py
- tests/gates_suite/test_protocol.py
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
Windows CI run 33521416410 (tracked by T-3659): all 10 tests in tests/gates_suite/test_protocol.py fail on win32 only, every one with the identical shape `assert v is not None` / `assert None is not None` -- protocol_summary_gate (src/frob/gates/_protocol_summary.py) returns ZERO PROTO002/PROTO003/PROTO004 violations where the test expects exactly one, across Python, Rust, and TypeScript fixtures and across the verification/ordering/cleanup rule families alike. This is one systemic root cause, not 10 independent ones.

Diagnostic lead (not yet a confirmed fix): the captured log for test_state_never_established_is_an_error shows
  WARNING frob.graph.summary:summary.py:600 T-0745: 1 function(s) not reachable from any entrypoint: ('C:/Users/runneradmin/AppData/Local/Temp/pytest-of-runneradmin/pytest-0/test_state_never_established_i0/src/a.py::enter',)
-- i.e. compute_protocol_summaries's own `universe` set carries 'enter' under an ABSOLUTE-path symref, while `_tagged_symbols_by_package`/`entrypoints` (built via `PurePosixPath`, edge.src) carries the SAME function under its correct repo-relative symref "src/a.py::enter". Two different symref spellings for one function means it is never found "reachable from itself" as an entrypoint, so it gets no summary at all, and PROTO002/003/004 (which all read off `result.summaries`) find nothing to report -- consistent with the shape "the WHOLE gate returns nothing" across every one of the 10 fixtures.

Where this could NOT be pinned down from source alone: every direct symref-construction call site checked (src/frob/graph/callgraph.py::_short_name_index/_resolve_edges via `f"{path}::{sym.qualname}"`, src/frob/gates/_dead_symbols.py::_package_files, src/frob/graph/__init__.py, src/frob/graph/reach.py) already builds/normalizes the relative-POSIX form correctly, and a reproduction attempt with an equivalent absolute tmp-dir-under-a-different-cwd on this POSIX machine did NOT reproduce the bug (protocol_summary_gate found the violation correctly with a properly relative symref). One genuine latent bug WAS found nearby -- src/frob/lang/__init__.py::_display_path relativizes against `Path.cwd()` instead of the caller's own repo root, which is wrong on general principle (produces an absolute-path fallback whenever cwd != root, on ANY platform) -- but it could not be confirmed as the actual cause of THIS failure (it appears to be used for logging/display only, not for the symrefs that feed `compute_protocol_summaries`/`callgraph.calls`, though its actual call sites were not exhaustively enumerated).

What would resolve this with certainty: a DEBUG-level Windows log capture (or a live win32 repro) showing (a) the exact `callgraph.calls` keys `build_call_graph`/`build_ordered_call_graph` produce for this fixture on win32 (to confirm whether they really carry the absolute-path spelling, and if so which of `_parse_package`/`_resolve_edges`/`_short_name_index`'s `path` loop variable is absolute rather than the repo-relative string `_package_files` is documented to always return), or (b) instrumented output from `_package_files(root, "src/a.py")` itself on win32 to check whether its `directory.is_dir()`/`.relative_to(root).as_posix()` path behaves differently than on POSIX (e.g. a case-sensitivity or short-vs-long-path-name mismatch between `root` as the test received it and `root` as `_package_files` re-derives `directory` from).

Filed per this campaign's process step 2 with a partial diagnosis rather than skipped, since the traceback does not PROVE this is unfixable from source -- it proves I could not pin the exact call site without windows-side instrumentation. Whoever works this ticket should start by adding a temporary DEBUG log of `callgraph.calls` keys inside `_package_protocol_violations`/`build_call_graph` and re-running the win32 leg (or reproducing via a Windows CI job / a genuinely mixed-separator tmp root) to confirm the exact divergence point, then fix the actual absolute-path leak at its source rather than patching around it in `_protocol_summary.py`.

Traceback evidence: scratchpad/win-33521-failures.txt lines 5554-16479 (all 10 failures, identical `assert v is not None` shape; full captured-log block for the first one at lines 6635-6636... see the WARNING line quoted above, immediately following each failure's traceback).

References T-3659 (tracking ticket for this campaign).
