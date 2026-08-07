---
id: T-0979
title: Resolve last 2 ARCH103 findings (format_paths/build_natives) and promote ARCH103
state: done
kind: bug
origin: human
created: '2026-07-27'
priority: medium
blocked_by:
- T-0976
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_fmt_directives.py
- src/frob/natives/_build.py
- frob.toml
- docs/audits/gates-quality.md
- frob.lock
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: frob.lock
  reason: frob ack of _format_one_path after its refactor touches frob.lock (digest
    store), a necessary side effect of the in-scope refactor
  actor: logan
  at: '2026-07-27'
evidence:
- tests/test_gates_fmt_directives.py::TestFormatPaths::test_check_mode_reports_without_writing
- tests/test_gates_fmt_directives.py::TestFormatPaths::test_write_mode_rewrites_file
- tests/unit/test_natives_build.py::TestBuildNatives::test_builds_declared_rust_natives
- tests/unit/test_natives_build.py::TestBuildNatives::test_skips_native_with_no_matching_crate_dir
- tests/unit/test_natives_build.py::TestBuildNatives::test_skips_non_rust_native
designated_repro_test: null
threat: null
component: null
---
T-0977 burned 22 of ARCH103's 24 live findings down via a real per-site
frob:waive ARCH103 (each with its own structural argument -- see
tickets.md's T-0977 Done report). The 2 remaining sites:

- src/frob/gates/_fmt_directives.py:288 format_paths
- src/frob/natives/_build.py:122 build_natives

are both in T-0976's concurrent ARCH001 burn-down finding list (same
files, same functions), and T-0977's own dispatch instructions say NOT to
touch functions that list names. These 2 are deliberately left live and
unwaived rather than risk colliding with T-0976's in-flight extraction.

Once T-0976 lands (or whichever ticket resolves these 2 functions'
ARCH001 finding), re-measure ARCH103 on both: if the extraction already
resolved the mixed-concern shape, nothing further is needed; if it is
still live post-extraction, add a reasoned frob:waive ARCH103 or extract
further, then promote [gates.severity] ARCH103 = "error" (frob.toml) once
truly at zero live unwaived findings.