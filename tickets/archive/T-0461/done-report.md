## Done report

Migrated the remaining bare-stdout `print()` call sites in the render
migration sweep's explicitly-named runner groups (vet/sys/release/dup/bind/
perf/mutate/stats) to go through `frob.render.Renderer` instead, closing the
gap T-0459's enforcement gate will check for. graph/ticket/deploy/outline/
xref/arch/docs/exports/serve/scaffold runners already had zero bare stdout
print/click.echo calls (migrated by earlier T-0419/20/21/448/460 work) and
needed no changes.

Every swap is a mechanical `print(x)` -> `Renderer.for_stream(sys.stdout).line(x)`
(or `.blank()` for a bare `print()`), which emits byte-identical output
(`Renderer._emit` is `print(line, file=stream)`) -- plain/non-TTY output is
unchanged for every migrated call site except one, disclosed below.

Deliberate output change: `frob sys doc`'s final `print(rendered, end="")`
used `end=""` to avoid a double trailing newline; `Renderer.line` always
terminates its line, so the call now strips the source's own trailing
newline before emitting (`rendered.danger_ok.rstrip("\n")`) through the
renderer -- net behavior is the same single trailing newline as before, not
a change, but implemented differently (documented per the T-0461 ticket
instruction to state any deliberate output changes).

`print(..., file=sys.stderr)` call sites (frob vet's hook-mode BLOCKED line,
frob bind's missing-path error) were left untouched: INV-RENDER-SOLE-STDOUT
(T-0459) governs stdout only, not stderr.

Out of scope, not touched: `src/frob/gates/**` (a sibling agent owns it, per
dispatch instructions) -- T-0459's own gate implementation is a separate
ticket landing after this one.

### Changed
```
 src/frob/app/bind_runner.py    | 13 +++++++-----
 src/frob/app/dup_runner.py     |  5 ++++-
 src/frob/app/mutate_runner.py  |  8 +++++---
 src/frob/app/perf_runner.py    | 15 ++++++++------
 src/frob/app/release_runner.py |  7 +++++--
 src/frob/app/stats_runner.py   |  9 +++++----
 src/frob/app/sys_runner.py     | 12 ++++++++---
 src/frob/app/vet_runner.py     | 46 +++++++++++++++++++++++++-----------------
 8 files changed, 73 insertions(+), 42 deletions(-)
```

### Evidence
- `tests/unit/test_app_runners_batch5.py::TestStatsRunner::test_text_mode_prints_report` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch5.py::TestBindRunner::test_list_bindings_text_mode` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch5.py::TestReleaseRunner::test_stamp_success_writes_manifest` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_perf.py::TestPerfProfileAndHeat::test_profile_then_heat_shows_hot_function` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_perf.py::TestPerfProfileAndHeat::test_heat_json_output_is_valid_json` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_sys_export.py::TestCliSysExport::test_k8s_export_is_valid_yaml` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_sys_doc.py::TestSysDocCli::test_renders_matrix_for_default_view` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_vet.py::TestHookMode::test_old_package_passes` (pytest node id, verified passing when recorded)
- `tests/test_mutate.py::test_run_mutations_survivors_when_tests_weak` (pytest node id, verified passing when recorded)
