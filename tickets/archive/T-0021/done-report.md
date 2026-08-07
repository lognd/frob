## Done report

Changed:
- src/frob/perf/__init__.py (new package: profile_command, load_artifact, heat, perf_rules, join_smells, render_bar, ProfileArtifact, HeatEntry, HeatReport, PerfError)
- src/frob/perf/_models.py, _profile.py, _heat.py, _rules.py (new)
- src/frob/gates/__init__.py::perf_gate (new, wired into run_gates as an additive "perf" job in _ALL_GATES)
- src/frob/app/perf_runner.py (new: `frob perf profile|heat` CLI runner)
- src/frob/app/config.py::AppConfig, Subcommand, AppConfig.from_external (perf_* fields wired)
- src/frob/app/app.py::App.__call__ (perf dispatch case)
- src/frob/__main__.py::_build_parser (perf/profile/heat argparse subcommands)
- docs/modules/perf.md (refreshed for actual coverage/caveats), docs/index.md (link added)
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
