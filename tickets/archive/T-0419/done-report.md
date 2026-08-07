## Done report

Added a TTY-only live task-list to `frob check` on top of the T-0460 render
vocabulary (`Progress`, `Renderer`). `run()` builds a `Renderer` bound to
stdout and, for non-`--json` runs, wraps the whole stage pipeline in
`renderer.write.progress("frob check")`; `Progress` is a no-op off a real
TTY (per its existing contract), so `--json`/piped/CI output is untouched.
`_run_all_stages`/`_run_all_detected`/`_run_auto_detected_stages`/
`_run_pinned_stage`/`_append_deploy_stages` now thread an optional
`progress`/`total` pair, updating the in-place bar once per language stage
and once per opt-in deploy stage as each completes, then clearing
automatically on the `with` block's exit so only the final summary
remains. Verified by eye with `script` (pty) showing the bar redraw
in-place and disappear before the PASS/FAIL summary line, and by piping
`frob check` through a non-tty pipe showing the exact prior plain output
(no ANSI, no bar artifacts).

### Changed
(no changed files detected)

### Evidence
(no evidence recorded)
