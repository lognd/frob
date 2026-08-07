---
id: T-0133
title: 'standalone tool install crashes: strata_core hard import in frob.lang (hotfixed);
  bundle or degrade natives properly'
state: done
kind: bug
origin: agent
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_lang_strata.py::TestStrataNativeParserUnavailable::test_parse_file_returns_native_parser_unavailable
- tests/unit/test_lang_strata.py::TestStrataNativeParserUnavailable::test_graph_build_skips_quietly
designated_repro_test: null
threat: null
component: null
---
T-0077's _walk_strata did a module-level 'import strata_core', making the maturin-built native extension a hard dependency of frob.lang -- every invocation of the standalone uv-tool-installed frob crashed with ModuleNotFoundError in ANY repo. Hotfixed with a guarded import: walk_strata returns Err('strata_core native extension unavailable...') when the parser is absent, so .strata files degrade to a per-file parse error instead of killing the process. Follow-up decisions this ticket tracks: (a) should supported_extensions() advertise .strata when the parser is missing (currently yes -- graph build will log the per-file Err; consider filtering), (b) ship strata-core (and frob-core) as wheels or optional extras so tool installs get full functionality, (c) add a CI job that uv-tool-installs the wheel in a clean env and runs frob check on a fixture repo to catch import-time regressions of the standalone binary.
## Done report

Completed the three hotfix follow-ups: (a) .strata stays advertised
with a NativeParserUnavailable sentinel distinguishing parser absence
(DEBUG, quiet everywhere -- 7 monkeypatched degrade tests) from real
syntax errors (still loud); (b) make install-tool pins the supported
full install (uv tool install --with both crates, proven end-to-end
twice) with docs/guides/install.md explaining bare/full/dev paths;
(c) CI standalone-install job installs the bare wheel in a clean venv,
hard-asserts frob --help, and greps frob check output for tracebacks
(continue-on-error until T-0135 lands -- its exit criterion). Two real
degrade gaps discovered and filed: T-0134 (_facts hard import) and
T-0135 (sys_gate imports strata before the opt-in check). Reviewer
APPROVED all dimensions. Verified at merge: 21 lang-strata tests
green, check baseline unchanged.