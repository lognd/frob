---
id: T-0021
title: 'frob.perf: profiling, heat-maps, PERF linear-scan rules (docs/perf.md)'
state: done
kind: feature
origin: human
created: '2026-07-17'
blocked_by: []
parent: null
scope:
- src/frob/perf/**
- src/frob/policy/**
- src/frob/app/**
- src/frob/gates/__init__.py
- src/frob/__main__.py
- docs/perf.md
- docs/index.md
- tests/test_perf.py
- tests/system/test_cli_perf.py
- tickets/T-0021-frob-perf-profiling-heat-maps-perf-linear-scan-rules-docs-perf-md.md
evidence:
- tests/test_perf.py::test_perf001_fires_on_list_membership_in_loop
- tests/test_perf.py::test_perf001_does_not_fire_on_set_membership_in_loop
- tests/test_perf.py::test_perf001_does_not_fire_outside_a_loop
- tests/test_perf.py::test_perf002_fires_on_index_call_in_loop
- tests/test_perf.py::test_perf002_does_not_fire_outside_a_loop
- tests/test_perf.py::test_perf003_fires_on_nested_loop_equality_join
- tests/test_perf.py::test_perf003_does_not_fire_on_single_loop
- tests/test_perf.py::test_perf004_fires_on_sort_in_loop
- tests/test_perf.py::test_perf004_does_not_fire_on_sort_outside_a_loop
- tests/test_perf.py::test_profile_command_and_load_artifact_round_trip
- tests/test_perf.py::test_load_artifact_no_artifact_is_err
- tests/test_perf.py::test_heat_joins_pstats_rows_onto_symbol_spans
- tests/system/test_cli_perf.py::TestPerfProfileAndHeat::test_profile_then_heat_shows_hot_function
- tests/system/test_cli_perf.py::TestPerfProfileAndHeat::test_heat_json_output_is_valid_json
- tests/system/test_cli_perf.py::TestPerfProfileAndHeat::test_heat_without_artifact_fails_cleanly
- tests/system/test_cli_perf.py::TestCheckOnlyPerf::test_perf001_fixture_warns_but_check_exits_zero
attachments: []
---

## Done report

Changed:
- src/frob/perf/__init__.py (new package: profile_command, load_artifact, heat, perf_rules, join_smells, render_bar, ProfileArtifact, HeatEntry, HeatReport, PerfError)
- src/frob/perf/_models.py, _profile.py, _heat.py, _rules.py (new)
- src/frob/gates/__init__.py::perf_gate (new, wired into run_gates as an additive "perf" job in _ALL_GATES)
- src/frob/app/perf_runner.py (new: `frob perf profile|heat` CLI runner)
- src/frob/app/config.py::AppConfig, Subcommand, AppConfig.from_external (perf_* fields wired)
- src/frob/app/app.py::App.__call__ (perf dispatch case)
- src/frob/__main__.py::_build_parser (perf/profile/heat argparse subcommands)
- docs/perf.md (refreshed for actual coverage/caveats), docs/index.md (link added)
- tests/test_perf.py (new, unit), tests/system/test_cli_perf.py (new, system)

Evidence: see frontmatter evidence list (12 unit + 4 system node ids), all
passing under `uv run pytest tests/test_perf.py tests/system/test_cli_perf.py`.

Filed: T-0027 (cProfile masks workload exit code; profile_command cannot
detect failed runs -- found demoing `frob perf profile --tests` post-close),
T-0028 (frob check red at HEAD: 16 orphan docs DOC001 + ruff-format drift in
9 committed files; blocks the whole-repo exit-0 commit gate for every
ticket). T-0026 pre-exists, filed by prior session, unrelated to T-0021.

Gates: `frob check --ticket T-0021 --only gates` is clean for every gate
this ticket's diff can affect (SCOPE001, COV002, PERF001-004 self-check).
Two pre-existing, out-of-scope issues remain in the working tree from
before this session and are NOT part of this diff's own violations:
`src/frob/app/check_runner.py::_warn_if_polyglot` (uncommitted T-0022 work,
COV002) and `tickets/T-0026-*.md` (untracked ticket file, SCOPE001) --
both predate T-0021 and are outside its declared scope; not touched here.
The wider repo-level `frob check` also carries substantial pre-existing
debt (ruff-format drift in 8 untouched files, COV001/TEST001/TEST002/DOC001
baseline violations across hundreds of pre-existing symbols, DOC001 on
docs/index.md's whole per-command reference table since it uses backtick
references rather than markdown links) -- all present before this ticket
and unrelated to `frob.perf`; not in scope to fix under T-0021.
