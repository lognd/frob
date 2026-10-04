+++
id = "01M336K755F0B787MT62Y5GGSF"
title = "CLI shim announce_shim logs at INFO, leaking a stray line onto every shimmed command's stdout (breaks --json)"
type = "bug"
category = "triage"
priority = "critical"
points = 2
reporter = "human"
created = "2026-09-22T00:00:00Z"
updated = "2026-09-22T00:00:01Z"
aliases = ["T-5285"]
labels = ["milestone:0.534.0", "v1-cluster:G2"]
scope = ["src/frob/_cli_parsers/_shims.py"]
+++

CI run 35717833933 on dev tip 197238c35e: ~150 of the ~170 total ubuntu test failures share ONE root cause. src/frob/_cli_parsers/_shims.py::announce_shim (T-4690's one deprecation-shim mechanism, called by every deleted/renamed top-level CLI verb: arch, dup, map, outline, xref, gitlog, and more) logs its notice via `_log.info(...)`. frob's default logging config (src/frob/logging/config.toml, T-2979) routes INFO-level records to the STDOUT handler -- so every shimmed command's stdout is now prefixed with a literal "cli shim: arch -> check --only arch (ticket=T-4690 sunset=2026-12-01 past_sunset=False)" line before its real output, breaking json.loads() on every `--json` invocation of a shimmed command (confirmed directly: tests/system/test_cli_arch.py::test_json_is_valid's captured stdout starts with that exact line, then the real JSON). This explains the mass failure across tests/system/test_cli_arch.py, test_cli_dup.py, test_cli_map.py, test_cli_outline.py, test_cli_xref.py, test_cli_gitlog.py, test_cli_scale.py, test_system.py, and more -- all invoke a shimmed alias with --json.

Fix (already prototyped and verified locally, reverted before filing since I do not own a worktree lease yet): change `_log.info` to `_log.debug` in announce_shim -- the human-readable deprecation notice is already correctly delivered via the separate `Renderer.for_stream(sys.stderr, ...)` call right below it; the `_log.info` line is a redundant diagnostic duplicate, not user-facing, and DEBUG-level records are excluded by the stdout handler's own level=INFO threshold by default (T-2979), only surfacing via FROB_LOG_LEVEL.

Verify with: tests/unit/test_cli_shims.py (the shim's own suite, including TestAnnounceShim.test_never_writes_to_stdout -- confirm this test currently only checks the renderer's own write, not the logger, since it did not already catch this) plus a representative sample of the failing --json tests (tests/system/test_cli_arch.py::test_json_is_valid, test_cli_map.py::test_json_is_valid, test_cli_outline.py::test_json_is_valid, test_cli_dup.py::test_json_is_valid, test_cli_xref.py::test_json_is_valid).

## Failure log
- 2026-09-22 attempt 1: TICK015: dead worktree (no live process holds worktree <worktree>/.claude/worktrees/t-5285), requeued by frob check
